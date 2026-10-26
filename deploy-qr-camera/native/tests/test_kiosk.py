import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("native_kiosk", Path(__file__).parents[1] / "kiosk.py")
kiosk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kiosk)


def test_duplicate_launch_while_window_open_is_ignored_and_close_releases_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(kiosk, "find_browser", lambda: Path("msedge.exe"))
    commands = []

    class Browser:
        def wait(self):
            assert kiosk.run(tmp_path, popen=launch) is False
            return 0

    def launch(command, **kwargs):
        commands.append(command)
        return Browser()

    assert kiosk.run(tmp_path, popen=launch)
    assert kiosk.run(tmp_path, popen=launch)
    assert len(commands) == 2
    assert all(kiosk.DISPLAY_URL in command for command in commands)
    assert all("--edge-kiosk-type=fullscreen" in command for command in commands)
    assert all("--user-data-dir=" + str(tmp_path / "kiosk-browser") in command for command in commands)


def test_browser_failure_releases_lock_for_next_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(kiosk, "find_browser", lambda: Path("msedge.exe"))

    def fail(*args, **kwargs):
        raise OSError("Browser unavailable")

    with pytest.raises(OSError):
        kiosk.run(tmp_path, popen=fail)
    with pytest.raises(OSError):
        kiosk.run(tmp_path, popen=fail)


def test_nonzero_browser_exit_is_reported_to_task_scheduler(tmp_path, monkeypatch):
    monkeypatch.setattr(kiosk, "find_browser", lambda: Path("msedge.exe"))

    class Browser:
        def wait(self):
            return 9

    with pytest.raises(RuntimeError, match="code 9"):
        kiosk.run(tmp_path, popen=lambda *a, **kw: Browser())
