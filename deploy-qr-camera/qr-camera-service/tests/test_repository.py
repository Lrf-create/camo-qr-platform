from app.models import DetectionEvent
from app.repository import PortASubmissionRepository


class FakeCursor:
    def __init__(self, rowcount: int = 1):
        self.rowcount = rowcount
        self.executed = None
        self.params = None

    def execute(self, statement, params):
        self.executed = statement
        self.params = params

    def fetchone(self):
        return (42,) if self.rowcount else None

    def close(self):
        pass


class FakeConnection:
    def __init__(self, rowcount: int = 1):
        self.cursor_instance = FakeCursor(rowcount)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def event(content: str) -> DetectionEvent:
    return DetectionEvent(
        event="qr_detected",
        content=content,
        corners=((1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)),
        center=(1.5, 1.5),
        size={"width": 1.0, "height": 1.0},
        frame_width=3840,
        frame_height=2160,
        timestamp="2026-08-13T00:00:00+00:00",
    )


def test_inserts_uppercase_ready_and_preserves_original_token():
    connection = FakeConnection()
    repository = PortASubmissionRepository(lambda: connection)
    assert repository.mark_ready(event("QR-ABC-123"))
    assert connection.committed
    assert repository.last_submission_id == 42
    assert connection.cursor_instance.params[1] == "QR-ABC-123"
    assert "INSERT INTO public.port_a_submission" in connection.cursor_instance.executed
    assert "'READY'" in connection.cursor_instance.executed
    assert "UPDATE" not in connection.cursor_instance.executed


def test_rolls_back_if_insert_does_not_return_row():
    connection = FakeConnection(rowcount=0)
    assert not PortASubmissionRepository(lambda: connection).mark_ready(event("QR-ABC-123"))
    assert connection.rolled_back and not connection.committed


def test_each_scan_gets_a_distinct_session_id():
    connection = FakeConnection()
    repository = PortASubmissionRepository(lambda: connection)
    repository.mark_ready(event("A"))
    first = connection.cursor_instance.params[0]
    repository.mark_ready(event("B"))
    assert first != connection.cursor_instance.params[0]


def test_overlong_content_rejected_before_connecting():
    import pytest
    with pytest.raises(ValueError):
        PortASubmissionRepository(lambda: None).mark_ready(event("X" * 129))
