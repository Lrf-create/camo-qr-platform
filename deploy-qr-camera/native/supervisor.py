"""Start and supervise the local platform, scanner and camera as one application."""
from __future__ import annotations

import json
import logging
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "native"
PG_HOME = Path(json.loads((STATE / "installation.json").read_text(encoding="utf-8-sig"))["postgres_home"])
PG = PG_HOME / "pgsql/bin/pg_ctl.exe"
DATA = PG_HOME / "pgdata"
FLAGS = subprocess.CREATE_NO_WINDOW


def fetch_json(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.load(response)
    except Exception:
        return None


def main():
    logging.basicConfig(filename=STATE / "supervisor.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    lock = (STATE / "application.lock").open("a+b")
    lock.seek(0)
    if not lock.read(1):
        lock.write(b"0")
        lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return
    stop_file = STATE / "stop.request"
    stop_file.unlink(missing_ok=True)
    (STATE / "supervisor.pid").write_text(str(os.getpid()))
    children = {}
    logs = []
    try:
        logging.info("Runtime binary=%s exists=%s executable=%s", PG, PG.exists(), sys.executable)
        pg_env = os.environ.copy()
        pg_env["PATH"] = str(PG.parent) + os.pathsep + pg_env.get("PATH", "")
        with (STATE / "postgres-start.log").open("ab") as out:
            status = subprocess.run([str(PG), "status", "-D", str(DATA)],
                                    stdout=out, stderr=out, creationflags=FLAGS, env=pg_env)
            if status.returncode:
                subprocess.run([str(PG), "start", "-D", str(DATA), "-l", str(STATE / "postgres.log"),
                                "-w", "-t", "30"], check=True, stdout=out, stderr=out,
                               creationflags=FLAGS, env=pg_env)
        logging.info("Local PostgreSQL ready")
        missing_since = time.monotonic()
        while not stop_file.exists():
            for role in ("web", "qr", "worker", "camera"):
                child = children.get(role)
                if child is None or child.poll() is not None:
                    out = (STATE / (role + ".log")).open("ab", buffering=0)
                    logs.append(out)
                    child = subprocess.Popen([sys.executable, "-u", str(STATE / "runtime.py"), role],
                                             cwd=str(ROOT), stdout=out, stderr=out, creationflags=FLAGS)
                    children[role] = child
                    logging.info("Started %s pid=%s", role, child.pid)
            status = fetch_json("http://127.0.0.1:8001/status")
            if status and status.get("camera_connected"):
                missing_since = time.monotonic()
            elif time.monotonic() - missing_since > 60:
                # A camera driver can block read() without exiting. Restart only
                # this application's camera child, leaving platform and data intact.
                child = children["camera"]
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                missing_since = time.monotonic()
                logging.warning("Restarted camera after no delivered frames for 60 seconds")
            payload = {"pid": os.getpid(), "mode": "windows_native", "updated_at": time.time(),
                       "processes": {role: child.pid for role, child in children.items()},
                       "camera_connected": bool(status and status.get("camera_connected"))}
            temporary = STATE / "status.tmp"
            temporary.write_text(json.dumps(payload), encoding="utf-8")
            temporary.replace(STATE / "status.json")
            time.sleep(3)
    except Exception:
        logging.exception("Application startup/runtime failed")
        raise
    finally:
        for child in children.values():
            if child.poll() is None:
                child.terminate()
        for child in children.values():
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
        for out in logs:
            out.close()
        subprocess.run([str(PG), "stop", "-D", str(DATA), "-m", "fast", "-w"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=FLAGS)
        (STATE / "status.json").unlink(missing_ok=True)
        (STATE / "supervisor.pid").unlink(missing_ok=True)
        stop_file.unlink(missing_ok=True)
        lock.close()
        logging.info("Application stopped")


if __name__ == "__main__":
    main()
