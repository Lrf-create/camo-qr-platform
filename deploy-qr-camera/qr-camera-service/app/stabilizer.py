from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Callable

from app.models import Detection, DetectionEvent


@dataclass
class DetectionStabilizer:
    confirm_frames: int = 3
    duplicate_seconds: float = 3.0
    clock: Callable[[], float] = monotonic

    def __post_init__(self) -> None:
        if self.confirm_frames < 1:
            raise ValueError("confirm_frames must be at least 1")
        if self.duplicate_seconds < 0:
            raise ValueError("duplicate_seconds cannot be negative")
        self._candidate: str | None = None
        self._candidate_count = 0
        self._last_emitted: str | None = None
        self._last_emitted_at: float | None = None

    def reset_candidate(self) -> None:
        self._candidate = None
        self._candidate_count = 0

    def accept(self, detection: Detection, now: float | None = None) -> DetectionEvent | None:
        current_time = self.clock() if now is None else now
        if detection.content != self._candidate:
            self._candidate = detection.content
            self._candidate_count = 1
        else:
            self._candidate_count += 1

        if self._last_emitted == detection.content and self._last_emitted_at is not None:
            if current_time - self._last_emitted_at <= self.duplicate_seconds:
                self._candidate_count = 0
                return None

        if self._candidate_count < self.confirm_frames:
            return None

        self._last_emitted = detection.content
        self._last_emitted_at = current_time
        self._candidate = None
        self._candidate_count = 0
        return DetectionEvent.from_detection(detection)
