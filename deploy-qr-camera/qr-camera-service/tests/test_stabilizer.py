from app.models import Detection
from app.stabilizer import DetectionStabilizer


def detection(content: str = "ABC123") -> Detection:
    return Detection(
        content=content,
        corners=((10.0, 10.0), (110.0, 10.0), (110.0, 110.0), (10.0, 110.0)),
        frame_width=3840,
        frame_height=2160,
    )


def test_emits_only_after_required_consecutive_frames():
    stabilizer = DetectionStabilizer(confirm_frames=3, duplicate_seconds=3.0)

    assert stabilizer.accept(detection(), now=0.0) is None
    assert stabilizer.accept(detection(), now=0.1) is None
    event = stabilizer.accept(detection(), now=0.2)

    assert event is not None
    assert event.content == "ABC123"
    assert event.center == (60.0, 60.0)


def test_suppresses_duplicate_until_duplicate_window_expires():
    stabilizer = DetectionStabilizer(confirm_frames=2, duplicate_seconds=3.0)

    assert stabilizer.accept(detection(), now=0.0) is None
    first = stabilizer.accept(detection(), now=0.1)
    assert first is not None

    assert stabilizer.accept(detection(), now=0.2) is None
    assert stabilizer.accept(detection(), now=3.2) is None
    second = stabilizer.accept(detection(), now=3.3)

    assert second is not None
    assert second.content == "ABC123"


def test_new_content_resets_confirmation_and_emits_independently():
    stabilizer = DetectionStabilizer(confirm_frames=2, duplicate_seconds=3.0)

    assert stabilizer.accept(detection("A"), now=0.0) is None
    assert stabilizer.accept(detection("B"), now=0.1) is None
    event = stabilizer.accept(detection("B"), now=0.2)

    assert event is not None
    assert event.content == "B"
