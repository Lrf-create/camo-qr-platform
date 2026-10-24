from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import CameraConfig


@dataclass
class CameraStatus:
    connected: bool = False
    frame_width: int | None = None
    frame_height: int | None = None
    fps: float | None = None
    pixel_format: str | None = None
    last_error: str | None = None


class Camera:
    def __init__(self, config: CameraConfig) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required for camera recognition") from exc
        self._cv2 = cv2
        self.config = config
        self.capture: Any | None = None
        self.status = CameraStatus()

    def open(self) -> None:
        backend = self._cv2.CAP_DSHOW if self.config.backend.lower() == "dshow" else self._cv2.CAP_ANY
        capture = self._cv2.VideoCapture(self.config.index, backend)
        if not capture.isOpened():
            capture.release()
            self.status = CameraStatus(last_error="camera_not_opened")
            raise RuntimeError("unable to open configured camera")

        if len(self.config.fourcc) == 4:
            fourcc = self._cv2.VideoWriter_fourcc(*self.config.fourcc)
            capture.set(self._cv2.CAP_PROP_FOURCC, fourcc)
        capture.set(self._cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        capture.set(self._cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        capture.set(self._cv2.CAP_PROP_FPS, self.config.fps)

        self.capture = capture
        self.status.connected = True
        self.status.frame_width = int(capture.get(self._cv2.CAP_PROP_FRAME_WIDTH))
        self.status.frame_height = int(capture.get(self._cv2.CAP_PROP_FRAME_HEIGHT))
        self.status.fps = capture.get(self._cv2.CAP_PROP_FPS) or None
        self.status.pixel_format = self.config.fourcc or None
        self.status.last_error = None

    def read(self) -> Any | None:
        if self.capture is None:
            raise RuntimeError("camera is not open")
        ok, frame = self.capture.read()
        if not ok:
            self.status.connected = False
            self.status.last_error = "frame_read_failed"
            return None
        self.status.connected = True
        # Use the captured frame as the source of truth; driver properties may be stale.
        self.status.frame_height, self.status.frame_width = frame.shape[:2]
        return frame

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.status.connected = False
