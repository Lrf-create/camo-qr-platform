from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from app.frame_receiver import FrameReceiver
from app.camera import Camera
from app.config import ServiceConfig
from app.detector import QRDetector
from app.models import DetectionEvent
from app.repository import PortASubmissionRepository
from app.stabilizer import DetectionStabilizer


@dataclass
class ServiceStatus:
    running: bool = False
    frames_processed: int = 0
    last_detection: DetectionEvent | None = None
    delivered_content: str | None = None
    database_written: bool = False
    last_error: str | None = None
    camera_connected: bool = False
    actual_frame_size: tuple[int | None, int | None] = (None, None)


class QRService:
    def __init__(self, config: ServiceConfig | None = None, repository: PortASubmissionRepository | None = None) -> None:
        self.config = config or ServiceConfig.from_env()
        self.repository = repository or PortASubmissionRepository.create_from_env()
        self.camera = Camera(self.config.camera)
        self.detector = QRDetector()
        self.stabilizer = DetectionStabilizer(
            confirm_frames=self.config.recognition.confirm_frames,
            duplicate_seconds=self.config.recognition.duplicate_seconds,
        )
        self.receiver = FrameReceiver(
            detector=self.detector, repository=self.repository,
            confirm_frames=self.config.recognition.confirm_frames,
            duplicate_seconds=self.config.recognition.duplicate_seconds,
        )
        self.status = ServiceStatus()
        self._latest_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="qr-camera", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        self.camera.close()
        self.status.running = False
        self.status.camera_connected = False

    def latest(self) -> DetectionEvent | None:
        with self._latest_lock:
            return self.status.last_detection

    def _run(self) -> None:
        self.status.running = True
        try:
            self.camera.open()
            self.status.camera_connected = True
            self.status.actual_frame_size = (self.camera.status.frame_width, self.camera.status.frame_height)
            while not self._stop_event.is_set():
                frame = self.camera.read()
                self.status.camera_connected = self.camera.status.connected
                self.status.actual_frame_size = (self.camera.status.frame_width, self.camera.status.frame_height)
                if frame is None:
                    self.status.last_error = self.camera.status.last_error
                    time.sleep(1)
                    self.camera.close()
                    try:
                        self.camera.open()
                    except RuntimeError as exc:
                        self.status.last_error = str(exc)
                    continue

                self.status.frames_processed += 1
                try:
                    result = self.receiver.process(self._apply_roi(frame))
                    self.status.last_error = self.receiver.last_error
                    if result:
                        with self._latest_lock:
                            self.status.last_detection = self.receiver.last_event
                            self.status.delivered_content = result["delivered_content"]
                            self.status.database_written = True
                except Exception:
                    self.status.database_written = False
                    self.status.last_error = "database_or_detection_failed"
                time.sleep(self.config.recognition.interval_ms / 1000)
        except Exception as exc:
            self.status.last_error = str(exc)
        finally:
            self.camera.close()
            self.status.running = False
            self.status.camera_connected = False

    def _apply_roi(self, frame: Any) -> Any:
        roi = self.config.recognition.roi
        if roi is None:
            return frame
        x, y, width, height = roi
        return frame[y : y + height, x : x + width]
