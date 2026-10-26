"""Open the public display in one dedicated, fullscreen browser session."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import msvcrt
import os
from pathlib import Path
import subprocess

STATE = Path(__file__).resolve().parent
DISPLAY_URL = "http://127.0.0.1:8000/display/sterile-supply/"


def find_browser() -> Path:
    for base in (os.getenv("ProgramFiles(x86)"), os.getenv("ProgramFiles"),
                 os.getenv("LOCALAPPDATA")):
        if not base:
            continue
        for relative in ("Microsoft/Edge/Application/msedge.exe",
                         "Google/Chrome/Application/chrome.exe"):
            path = Path(base) / relative
            if path.is_file():
                return path
    raise RuntimeError("Microsoft Edge or Google Chrome is required")


def browser_command(browser: Path, state: Path) -> list[str]:
    command = [str(browser), "--kiosk", DISPLAY_URL,
               "--user-data-dir=" + str(state / "kiosk-browser"),
               "--no-first-run", "--no-default-browser-check",
               "--disable-background-mode", "--hide-crash-restore-bubble"]
    if browser.name.lower() == "msedge.exe":
        command.append("--edge-kiosk-type=fullscreen")
    return command


def run(state: Path = STATE, *, popen=subprocess.Popen) -> bool:
    """Hold a lock until the dedicated browser exits; reject overlapping launches."""
    state.mkdir(parents=True, exist_ok=True)
    with (state / "kiosk.lock").open("a+b") as lock:
        lock.seek(0)
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            logging.info("Display already open; ignored duplicate request")
            return False
        try:
            browser = find_browser()
            logging.info("Opening fullscreen display with %s", browser.name)
            child = popen(browser_command(browser, state), stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            code = child.wait()
            if code != 0:
                raise RuntimeError(f"Browser exited with code {code}")
            logging.info("Display browser closed; background scanning remains active")
            return True
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        handlers=[RotatingFileHandler(STATE / "kiosk.log", maxBytes=1_000_000,
                                                      backupCount=2, encoding="utf-8")],
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        run()
    except Exception:
        logging.exception("Fullscreen display startup failed")
        raise SystemExit(1)
