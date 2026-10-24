"""Windows-native application entry points. No Docker dependency."""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent / "medical_device_poc"


def load_environment():
    settings = json.loads((ROOT / "native/settings.json").read_text(encoding="utf-8"))
    os.environ.update({key: str(value) for key, value in settings.items()})
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.prod"
    sys.path.insert(0, str(PROJECT / "src"))
    return settings


def main():
    load_environment()
    role = sys.argv[1]
    if role == "web":
        from config.wsgi import application
        from waitress import serve
        serve(application, host="127.0.0.1", port=8000, threads=4)
    elif role == "qr":
        sys.path.insert(0, str(ROOT / "qr-camera-service"))
        from app.docker_api import create_app
        import uvicorn
        # The frame API runs as an ordinary Windows process despite its legacy name.
        uvicorn.run(create_app(), host="127.0.0.1", port=8001, log_level="warning")
    elif role == "camera":
        runpy.run_path(str(ROOT / "qr-camera-service/camera_bridge/bridge.py"), run_name="__main__")
    elif role == "worker":
        import django
        django.setup()
        from django.core.management import call_command
        call_command("process_submissions")
    elif role == "manage":
        sys.argv = [str(PROJECT / "manage.py"), *sys.argv[2:]]
        runpy.run_path(str(PROJECT / "manage.py"), run_name="__main__")
    else:
        raise ValueError("Unknown application role")


if __name__ == "__main__":
    main()
