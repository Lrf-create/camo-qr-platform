from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_desktop_launcher_scripts_exist_and_start_django_server():
    start_script = PROJECT_ROOT / "scripts" / "start_platform.ps1"
    cmd_wrapper = PROJECT_ROOT / "scripts" / "start_platform.cmd"

    assert start_script.exists()
    assert cmd_wrapper.exists()

    start_content = start_script.read_text(encoding="utf-8")
    assert "manage.py" in start_content
    assert "runserver" in start_content
    assert "127.0.0.1:8000" in start_content
    assert "Start-Process" in start_content
    assert "http://127.0.0.1:8000/" in start_content

    cmd_content = cmd_wrapper.read_text(encoding="utf-8")
    assert "powershell" in cmd_content.lower()
    assert "start_platform.ps1" in cmd_content
