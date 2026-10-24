from __future__ import annotations

import os
import sys
import threading
import time

from django.conf import settings
from django.db import close_old_connections

_started = False
_lock = threading.Lock()


def start_auto_processor() -> None:
    global _started
    if not _should_start_auto_processor():
        return

    with _lock:
        if _started:
            return
        thread = threading.Thread(target=_run_loop, name="submission-auto-processor", daemon=True)
        thread.start()
        _started = True


def _should_start_auto_processor() -> bool:
    if len(sys.argv) < 2 or sys.argv[1] != "runserver":
        return False
    if "--noreload" not in sys.argv and os.environ.get("RUN_MAIN") != "true":
        return False
    return os.environ.get("DISABLE_SUBMISSION_AUTO_PROCESSOR") != "1"


def _run_loop() -> None:
    while True:
        close_old_connections()
        try:
            from apps.submissions.services import process_all_ready_once

            process_all_ready_once(require_running=False)
        except Exception:
            # Keep the web process alive; the next poll can recover after transient DB errors.
            pass
        finally:
            close_old_connections()
        time.sleep(settings.POLL_INTERVAL_SECONDS)
