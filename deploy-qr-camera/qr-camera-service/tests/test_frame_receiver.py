from app.frame_receiver import FrameReceiver
from app.models import Detection, DetectionEvent


class FakeDetector:
    def __init__(self, detections):
        self.detections = detections

    def detect(self, frame):
        return self.detections


class FakeRepository:
    def __init__(self):
        self.events = []

    def mark_ready(self, event):
        self.events.append(event)
        return True


def detection(content="QR-001"):
    return Detection(
        content=content,
        corners=((1.0, 1.0), (5.0, 1.0), (5.0, 5.0), (1.0, 5.0)),
        frame_width=3840,
        frame_height=2160,
    )


def test_processes_frame_only_after_stable_detection_and_returns_delivery():
    repository = FakeRepository()
    receiver = FrameReceiver(
        detector=FakeDetector([detection()]),
        repository=repository,
        confirm_frames=2,
        duplicate_seconds=3.0,
    )

    assert receiver.process(object()) is None
    result = receiver.process(object())

    assert result is not None
    assert result["content"] == "QR-001"
    assert result["delivered_content"] == "QR-001ready"
    assert len(repository.events) == 1


def test_does_not_deliver_when_database_update_fails():
    class FailedRepository(FakeRepository):
        def mark_ready(self, event):
            return False

    receiver = FrameReceiver(
        detector=FakeDetector([detection()]),
        repository=FailedRepository(),
        confirm_frames=1,
        duplicate_seconds=3.0,
    )

    assert receiver.process(object()) is None
    assert receiver.last_error == "port_a_submission_not_found"


def test_stationary_qr_is_not_resubmitted_after_time_window():
    repository = FakeRepository()
    receiver = FrameReceiver(FakeDetector([detection()]), repository, confirm_frames=1, duplicate_seconds=0)
    assert receiver.process(None)
    for _ in range(20):
        assert receiver.process(None) is None
    assert len(repository.events) == 1
    receiver.detector.detections = []
    receiver.process(None)
    receiver.detector.detections = [detection()]
    assert receiver.process(None)
    assert len(repository.events) == 2


def test_blank_frame_resets_confirmation_and_multiple_codes_never_submit():
    repository = FakeRepository()
    detector = FakeDetector([detection()])
    receiver = FrameReceiver(detector, repository, confirm_frames=2, duplicate_seconds=0)
    assert receiver.process(None) is None
    detector.detections = []
    receiver.process(None)
    detector.detections = [detection()]
    assert receiver.process(None) is None
    detector.detections = [detection(), detection("OTHER")]
    assert receiver.process(None) is None
    assert receiver.last_error == "multiple_qr_codes"
    assert not repository.events
