from fastapi.testclient import TestClient
import cv2
import numpy as np

from app.docker_api import MAX_FRAME_BYTES, create_app
from app.frame_receiver import FrameReceiver
from app.models import Detection


class Repository:
    submission_id = 3

    def __init__(self):
        self.events = []

    def mark_ready(self, event):
        self.events.append(event)
        return True


class Detector:
    def detect(self, frame):
        return [Detection(content="QR-DEMO", corners=((0., 0.), (1., 0.), (1., 1.), (0., 1.)),
                          frame_width=frame.shape[1], frame_height=frame.shape[0])]


def test_http_frames_confirm_before_database_write_and_expose_result():
    repository = Repository()
    receiver = FrameReceiver(detector=Detector(), repository=repository, confirm_frames=2)
    client = TestClient(create_app(receiver))
    _, jpeg = cv2.imencode('.jpg', np.zeros((100, 200, 3), dtype=np.uint8))
    first = client.post('/frames', content=jpeg.tobytes(), headers={'Content-Type': 'image/jpeg'})
    assert first.status_code == 200 and first.json()['result'] is None
    assert repository.events == []
    second = client.post('/frames', content=jpeg.tobytes(), headers={'Content-Type': 'image/jpeg'})
    assert second.json()['result']['database_written'] is True
    assert len(repository.events) == 1
    assert client.get('/latest').json()['delivered_content'] == 'QR-DEMOready'
    assert client.get('/status').json()['actual_frame_size'] == [200, 100]


def test_rejects_invalid_and_oversized_uploads_without_database_write():
    repository = Repository()
    client = TestClient(create_app(FrameReceiver(detector=Detector(), repository=repository)))
    assert client.post('/frames', content=b'bad').status_code == 415
    assert client.post('/frames', content=b'bad', headers={'Content-Type': 'image/jpeg'}).status_code == 400
    assert client.post('/frames', content=b'x' * (MAX_FRAME_BYTES + 1),
                       headers={'Content-Type': 'image/jpeg'}).status_code == 413
    assert repository.events == []
