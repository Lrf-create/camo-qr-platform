"""Continuously drain the camera; deliver only the newest distinct frame."""
from __future__ import annotations

import http.client
import json
import logging
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

import cv2


class LatestFrameBuffer:
    """A single-slot buffer: slow consumers never build a queue of old frames."""
    def __init__(self):
        self.condition = threading.Condition()
        self.sequence = 0
        self.frame = None
        self.captured_at = 0.0
        self.closed = False

    def publish(self, frame, captured_at):
        with self.condition:
            self.sequence += 1
            self.frame = frame
            self.captured_at = captured_at
            self.condition.notify_all()

    def wait_after(self, sequence, timeout=2):
        with self.condition:
            self.condition.wait_for(lambda: self.sequence > sequence or self.closed, timeout)
            if self.sequence <= sequence:
                return None
            return self.sequence, self.frame, self.captured_at

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()


class FrameSender:
    """Reuse the local HTTP connection rather than reconnecting for every frame."""
    def __init__(self, url):
        target = urlsplit(url)
        connection_type = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
        self.connection = connection_type(target.hostname, target.port, timeout=3)
        self.path = target.path or "/frames"
        if target.query:
            self.path += "?" + target.query

    def send(self, jpeg):
        self.connection.request("POST", self.path, body=jpeg, headers={"Content-Type": "image/jpeg"})
        response = self.connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError("frame_api_http_" + str(response.status))
        return json.loads(body)

    def close(self):
        self.connection.close()


def capture_frames(camera, buffer, stop):
    try:
        while not stop.is_set():
            ok, frame = camera.read()
            if not ok:
                logging.warning("Camera read failed; reopening")
                break
            buffer.publish(frame, time.monotonic())
    except Exception:
        logging.exception("Camera capture failed")
    finally:
        camera.release()
        buffer.close()


def deliver_frames(buffer, sender, interval, metrics_path):
    sequence = 0
    next_due = time.monotonic()
    measured_at = next_due
    initial_sequence = 0
    sent = 0
    ages = []
    durations = []
    while True:
        delay = next_due - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        item = buffer.wait_after(sequence)
        if item is None:
            if buffer.closed:
                return
            continue
        sequence, frame, captured_at = item
        started = time.monotonic()
        next_due = started + interval
        age = (started - captured_at) * 1000
        encoded, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not encoded:
            continue
        try:
            payload = sender.send(jpeg.tobytes())
            sent += 1
            ages.append(age)
            durations.append((time.monotonic() - started) * 1000)
            if payload.get("result"):
                logging.info("QR submitted: %s", payload["result"])
            if payload.get("warning"):
                logging.warning("QR warning: %s", payload["warning"])
        except Exception as exc:
            logging.warning("Frame delivery failed: %s", type(exc).__name__)
            sender.close()
            time.sleep(1)
        elapsed = time.monotonic() - measured_at
        if elapsed >= 5:
            metrics = {
                "updated_at": time.time(),
                "capture_fps": round((sequence - initial_sequence) / elapsed, 2),
                "delivery_fps": round(sent / elapsed, 2),
                "mean_frame_age_ms": round(sum(ages) / len(ages), 2) if ages else None,
                "mean_delivery_ms": round(sum(durations) / len(durations), 2) if durations else None,
                "max_pending_frames": 1,
            }
            temporary = metrics_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(metrics), encoding="utf-8")
            temporary.replace(metrics_path)
            measured_at = time.monotonic()
            initial_sequence = sequence
            sent = 0
            ages.clear()
            durations.clear()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    root = Path(__file__).resolve().parents[2]
    config_path = root / "camera-config.json"
    if config_path.exists():
        for key, value in json.loads(config_path.read_text(encoding="utf-8-sig")).items():
            os.environ.setdefault(key, str(value))
    url = os.getenv("QR_BRIDGE_URL", "http://127.0.0.1:8001/frames")
    camera_name = os.getenv("QR_CAMERA_NAME", "Camo")
    interval = float(os.getenv("QR_BRIDGE_INTERVAL", "0.1"))
    if interval <= 0:
        raise ValueError("QR_BRIDGE_INTERVAL must be positive")
    metrics_dir = root / "native"
    metrics_path = (metrics_dir if metrics_dir.is_dir() else root) / "camera-metrics.json"
    while True:
        from cv2_enumerate_cameras import enumerate_cameras
        cameras = list(enumerate_cameras(cv2.CAP_DSHOW))
        matches = [c for c in cameras if camera_name.lower() in c.name.lower()]
        if not matches:
            logging.error("Camera named %s not found; open Camo Studio", camera_name)
            time.sleep(5)
            continue
        index = matches[0].index
        logging.info("Selected %s (index %s), latest-frame capture interval=%s", matches[0].name, index, interval)
        camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not camera.isOpened():
            camera.release()
            time.sleep(5)
            continue
        fourcc = os.getenv("QR_CAMERA_FOURCC", "YUY2")
        if len(fourcc) == 4:
            camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(os.getenv("QR_CAMERA_WIDTH", "1280")))
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(os.getenv("QR_CAMERA_HEIGHT", "720")))
        camera.set(cv2.CAP_PROP_FPS, 30)
        buffer = LatestFrameBuffer()
        stop = threading.Event()
        reader = threading.Thread(target=capture_frames, args=(camera, buffer, stop), name="camo-capture", daemon=True)
        sender = FrameSender(url)
        reader.start()
        try:
            deliver_frames(buffer, sender, interval, metrics_path)
        finally:
            sender.close()
            stop.set()
            reader.join(timeout=3)
            if reader.is_alive():
                raise RuntimeError("Camera driver blocked during shutdown")
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
