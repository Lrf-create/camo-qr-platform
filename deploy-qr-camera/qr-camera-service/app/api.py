from __future__ import annotations

from typing import Any

from app.config import ServiceConfig
from app.service import QRService


def create_app(service: QRService | None = None) -> Any:
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise RuntimeError("fastapi is required to run the HTTP API") from exc

    app = FastAPI(title="QR Camera Service", version="0.2.0")
    active_service = service or QRService(ServiceConfig.from_env())

    @app.on_event("startup")
    def startup() -> None:
        active_service.start()

    @app.on_event("shutdown")
    def shutdown() -> None:
        active_service.stop()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status")
    def status() -> dict[str, Any]:
        state = active_service.status
        return {
            "running": state.running,
            "camera_connected": state.camera_connected,
            "frames_processed": state.frames_processed,
            "actual_frame_size": list(state.actual_frame_size),
            "last_error": state.last_error,
            "database_written": state.database_written,
            "delivered_content": state.delivered_content,
            "latest_detection": state.last_detection.to_dict() if state.last_detection else None,
        }

    @app.get("/latest")
    def latest() -> dict[str, Any]:
        event = active_service.latest()
        return {
            "detection": event.to_dict() if event else None,
            "delivered_content": active_service.status.delivered_content,
            "database_written": active_service.status.database_written,
        }

    return app
