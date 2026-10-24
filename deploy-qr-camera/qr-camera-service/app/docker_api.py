"""HTTP frame receiver for Docker; the Windows bridge owns the camera."""
from contextlib import asynccontextmanager
import os
import threading
import time

import cv2
import numpy as np
import psycopg
from fastapi import FastAPI, HTTPException, Request

from app.frame_receiver import FrameReceiver

MAX_FRAME_BYTES = 8 * 1024 * 1024


def create_app(receiver=None):
    active = receiver or FrameReceiver(
        confirm_frames=int(os.getenv("QR_CONFIRM_FRAMES", "3")),
        duplicate_seconds=float(os.getenv("QR_DUPLICATE_SECONDS", "3")),
    )
    lock = threading.Lock()
    state = {"last_frame_at": None, "actual_frame_size": None, "last_error": None}

    @asynccontextmanager
    async def lifespan(app):
        yield

    app = FastAPI(title="QR Camera Docker Service", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "http_frames"}

    @app.get("/status")
    def status():
        with lock:
            last_frame = state["last_frame_at"]
            return {
                "running": True,
                "mode": "http_frames",
                "camera_connected": last_frame is not None and time.time() - last_frame < 10,
                "frames_processed": active.frames_received,
                "actual_frame_size": state["actual_frame_size"],
                "last_frame_at": last_frame,
                "last_error": state["last_error"] or active.last_error,
                "database_written": active.last_event is not None,
                "latest_detection": active.last_event.to_dict() if active.last_event else None,
            }

    @app.get("/latest")
    def latest():
        with lock:
            event = active.last_event
            return {
                "detection": event.to_dict() if event else None,
                "delivered_content": f"{event.content}ready" if event else None,
                "database_written": event is not None,
            }

    @app.get("/database/health")
    def database_health():
        try:
            with psycopg.connect(os.environ["QR_DATABASE_URL"], connect_timeout=5) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM public.port_a_submission LIMIT 0")
            return {"status": "ok", "mode": "insert_per_scan"}
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, "Database or submission table unavailable") from None

    @app.post("/frames")
    async def frames(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "image/jpeg":
            raise HTTPException(415, "Send a JPEG body with Content-Type: image/jpeg")
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > MAX_FRAME_BYTES:
                raise HTTPException(413, "Frame exceeds 8 MiB")
            data.extend(chunk)
        if not data:
            raise HTTPException(400, "Empty JPEG")
        # Run OpenCV and database I/O outside the event loop. Serialize the
        # stabilizer and its status across concurrent frame requests.
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(process_frame, bytes(data))

    def process_frame(data):
        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(400, "Invalid JPEG")
        if frame.shape[0] * frame.shape[1] > 16_000_000:
            raise HTTPException(413, "Frame exceeds 16 megapixels")
        with lock:
            state["last_frame_at"] = time.time()
            state["actual_frame_size"] = [frame.shape[1], frame.shape[0]]
            try:
                result = active.process(frame)
            except Exception:
                state["last_error"] = "database_or_detection_failed"
                raise HTTPException(503, "Frame processing failed; check database connectivity") from None
            state["last_error"] = active.last_error
            if active.last_error and active.last_error not in {"multiple_qr_codes", "qr_content_too_long"}:
                raise HTTPException(503, active.last_error)
            return {"accepted": True, "result": result, "warning": active.last_error}

    return app
