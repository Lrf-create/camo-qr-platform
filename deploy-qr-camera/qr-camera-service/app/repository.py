from __future__ import annotations
from typing import Any, Callable
from uuid import uuid4
from app.models import DetectionEvent

INSERT_PORT_A_SUBMISSION = """
INSERT INTO public.port_a_submission
    (session_id, qr_token_raw, status, result_code, result_message,
     created_at, ready_at, processed_at)
VALUES (%s, %s, 'READY', '', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
RETURNING id
"""

class PortASubmissionRepository:
    """Create one display-only record per scan without overwriting history."""
    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory
        self.last_submission_id = None

    def mark_ready(self, event: DetectionEvent) -> bool:
        if not event.content or len(event.content) > 128:
            raise ValueError("QR content must contain 1 to 128 characters")
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(INSERT_PORT_A_SUBMISSION, (uuid4(), event.content))
            row = cursor.fetchone()
            if row is None:
                connection.rollback()
                return False
            connection.commit()
            self.last_submission_id = row[0]
            return True
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    @staticmethod
    def create_from_env() -> "PortASubmissionRepository":
        import os
        import psycopg
        url = os.environ["QR_DATABASE_URL"]
        return PortASubmissionRepository(lambda: psycopg.connect(url, connect_timeout=5))
