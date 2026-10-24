from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    width: int = 3840
    height: int = 2160
    fps: int = 30
    backend: str = "dshow"
    fourcc: str = "MJPG"


@dataclass(frozen=True)
class RecognitionConfig:
    confirm_frames: int = 3
    duplicate_seconds: float = 3.0
    interval_ms: int = 100
    roi: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class ServiceConfig:
    camera: CameraConfig = CameraConfig()
    recognition: RecognitionConfig = RecognitionConfig()
    show_window: bool = False

    @classmethod
    def from_env(cls) -> "ServiceConfig":
        import os

        roi_text = os.getenv("QR_ROI", "").strip()
        roi = None
        if roi_text:
            values = tuple(int(value.strip()) for value in roi_text.split(","))
            if len(values) != 4:
                raise ValueError("QR_ROI must contain x,y,width,height")
            roi = values  # type: ignore[assignment]

        return cls(
            camera=CameraConfig(
                index=int(os.getenv("QR_CAMERA_INDEX", "0")),
                width=int(os.getenv("QR_CAMERA_WIDTH", "3840")),
                height=int(os.getenv("QR_CAMERA_HEIGHT", "2160")),
                fps=int(os.getenv("QR_CAMERA_FPS", "30")),
                backend=os.getenv("QR_CAMERA_BACKEND", "dshow"),
                fourcc=os.getenv("QR_CAMERA_FOURCC", "MJPG").upper(),
            ),
            recognition=RecognitionConfig(
                confirm_frames=int(os.getenv("QR_CONFIRM_FRAMES", "3")),
                duplicate_seconds=float(os.getenv("QR_DUPLICATE_SECONDS", "3")),
                interval_ms=int(os.getenv("QR_INTERVAL_MS", "100")),
                roi=roi,
            ),
            show_window=os.getenv("QR_SHOW_WINDOW", "false").lower() in {"1", "true", "yes"},
        )
