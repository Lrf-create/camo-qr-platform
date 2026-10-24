import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

from camera_bridge.bridge import FrameSender, LatestFrameBuffer


def test_slow_consumer_gets_latest_frame_and_never_reuses_same_frame():
    buffer = LatestFrameBuffer()
    for frame in range(100):
        buffer.publish(frame, float(frame))
    sequence, frame, captured_at = buffer.wait_after(0, timeout=0)
    assert (sequence, frame, captured_at) == (100, 99, 99.0)
    assert buffer.wait_after(sequence, timeout=0) is None
    buffer.publish("new-frame", 101.0)
    assert buffer.wait_after(sequence, timeout=0) == (101, "new-frame", 101.0)


def test_camera_close_wakes_consumer_without_replaying_old_frames():
    buffer = LatestFrameBuffer()
    buffer.publish("frame", 1.0)
    buffer.close()
    assert buffer.wait_after(0, timeout=0) == (1, "frame", 1.0)
    assert buffer.wait_after(1, timeout=0) is None


def test_frame_sender_reuses_connection_for_successive_requests():
    peers = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            peers.append(self.client_address[1])
            assert self.rfile.read(int(self.headers["Content-Length"])) == b"jpeg-frame"
            body = json.dumps({"accepted": True, "result": None}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    sender = FrameSender(f"http://127.0.0.1:{server.server_port}/frames")
    try:
        for _ in range(3):
            assert sender.send(b"jpeg-frame")["accepted"] is True
        assert len(peers) == 3
        assert len(set(peers)) == 1
    finally:
        sender.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
