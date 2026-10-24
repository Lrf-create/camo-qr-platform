from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Tuple

Point = Tuple[float, float]
Corners = Tuple[Point, Point, Point, Point]


@dataclass(frozen=True)
class Detection:
    content: str
    corners: Corners
    frame_width: int
    frame_height: int

    @property
    def center(self) -> Point:
        x = sum(point[0] for point in self.corners) / 4
        y = sum(point[1] for point in self.corners) / 4
        return (x, y)

    @property
    def size(self) -> dict[str, float]:
        width = max(point[0] for point in self.corners) - min(point[0] for point in self.corners)
        height = max(point[1] for point in self.corners) - min(point[1] for point in self.corners)
        return {"width": width, "height": height}


@dataclass(frozen=True)
class DetectionEvent:
    event: str
    content: str
    corners: Corners
    center: Point
    size: dict[str, float]
    frame_width: int
    frame_height: int
    timestamp: str

    @classmethod
    def from_detection(cls, detection: Detection, now: datetime | None = None) -> "DetectionEvent":
        timestamp = now or datetime.now(timezone.utc)
        return cls(
            event="qr_detected",
            content=detection.content,
            corners=detection.corners,
            center=detection.center,
            size=detection.size,
            frame_width=detection.frame_width,
            frame_height=detection.frame_height,
            timestamp=timestamp.isoformat(),
        )

    def to_dict(self) -> dict:
        return {
            "event": self.event,
            "content": self.content,
            "corners": [list(point) for point in self.corners],
            "center": list(self.center),
            "size": self.size,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "timestamp": self.timestamp,
        }
