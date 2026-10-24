from __future__ import annotations

from typing import Any

from app.detector import QRDetector
from app.models import DetectionEvent
from app.repository import PortASubmissionRepository
from app.stabilizer import DetectionStabilizer


class FrameReceiver:
    def __init__(
        self,
        detector: QRDetector | Any | None = None,
        repository: PortASubmissionRepository | Any | None = None,
        confirm_frames: int = 3,
        duplicate_seconds: float = 3.0,
    ) -> None:
        self.detector = detector or QRDetector()
        self.repository = repository or PortASubmissionRepository.create_from_env()
        self.stabilizer = DetectionStabilizer(confirm_frames, duplicate_seconds)
        self.last_error: str | None = None
        self.frames_received = 0
        self.last_event: DetectionEvent | None = None
        self._visible_content: str | None = None
        self._submitted_content: str | None = None
        self._empty_frames = 0

    def process(self, frame: Any) -> dict[str, Any] | None:
        self.frames_received += 1
        self.last_error = None
        detections = self.detector.detect(frame)
        if len(detections) != 1:
            self.stabilizer.reset_candidate()
            self._empty_frames += 1
            if not detections and self._empty_frames >= self.stabilizer.confirm_frames:
                self._submitted_content = None
                self._visible_content = None
            if len(detections) > 1:
                self.last_error = "multiple_qr_codes"
            return None
        self._empty_frames = 0
        for detection in detections:
            if len(detection.content) > 128:
                self.last_error = "qr_content_too_long"
                return None
            if detection.content != self._visible_content:
                self._visible_content = detection.content
                self._submitted_content = None
                self.stabilizer.reset_candidate()
            if detection.content == self._submitted_content:
                return None
            event = self.stabilizer.accept(detection)
            if event is None:
                continue
            if not self.repository.mark_ready(event):
                self.last_error = "port_a_submission_not_found"
                return None
            self.last_event = event
            self._submitted_content = event.content
            return {
                "event": "qr_detected",
                "content": event.content,
                "delivered_content": f"{event.content}ready",
                "database_written": True,
                "submission_id": getattr(self.repository, "last_submission_id", None),
            }
        return None
