from __future__ import annotations

from typing import Any

from app.models import Detection


class QRDetector:
    def __init__(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required for camera recognition") from exc
        self._cv2 = cv2
        self._detector = cv2.QRCodeDetector()

    def detect(self, frame: Any) -> list[Detection]:
        height, width = frame.shape[:2]
        results: list[Detection] = []

        try:
            ok, decoded, points, _ = self._detector.detectAndDecodeMulti(frame)
        except (AttributeError, self._cv2.error):
            ok, decoded, points = False, [], None

        if ok and points is not None:
            for content, raw_points in zip(decoded, points):
                if content and raw_points is not None:
                    results.append(self._build_detection(content, raw_points, width, height))
            if results:
                return results

        content, points, _ = self._detector.detectAndDecode(frame)
        if content and points is not None:
            results.append(self._build_detection(content, points, width, height))
        return results

    @staticmethod
    def _build_detection(content: str, points: Any, width: int, height: int) -> Detection:
        flattened = points.reshape(-1, 2)[:4]
        corners = tuple((float(point[0]), float(point[1])) for point in flattened)
        if len(corners) != 4:
            raise ValueError("QR detector returned an invalid corner set")
        return Detection(content=content, corners=corners, frame_width=width, frame_height=height)  # type: ignore[arg-type]
