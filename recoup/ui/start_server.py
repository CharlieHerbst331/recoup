"""Single-process Sandbox startup for the workbench; design/02 §4.5, §5.9, §6."""

import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def healthy():
    try:
        with urlopen("http://127.0.0.1:8501/_stcore/health", timeout=1) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def ensure_server(data=Path("/data")):
    source = data / "app"
    config = hashlib.sha256(
        json.dumps(
            [os.environ.get(key, "") for key in ("OPENAI_API_KEY", "RECOUP_ACCESS_SECRET")]
        ).encode()
    ).hexdigest()
    with (data / "start.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_file = data / "server-state.json"
        try:
            state = json.loads(state_file.read_text())
        except (OSError, ValueError):
            state = {}
        if healthy():
            if state.get("config") == config:
                return
            # Only terminate the recorded Recoup process, never an unrelated reused PID.
            pid = state.get("pid")
            command = Path(f"/proc/{pid}/cmdline").read_bytes()
            if b"streamlit" not in command or b"workbench.py" not in command:
                raise RuntimeError("Workspace process does not match")
            os.kill(pid, signal.SIGTERM)
            for _ in range(40):
                if not healthy():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError("Workspace is still stopping")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(source / "recoup/ui/workbench.py"),
                "--server.address=0.0.0.0",
                "--server.port=8501",
                "--server.headless=true",
                "--server.fileWatcherType=none",
                "--server.enableXsrfProtection=true",
                "--server.enableCORS=true",
                "--client.showErrorDetails=none",
                "--browser.gatherUsageStats=false",
            ],
            cwd=source,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        state_file.write_text(json.dumps({"pid": process.pid, "config": config}))
        for _ in range(60):
            if healthy():
                return
            if process.poll() is not None:
                break
            time.sleep(0.2)
        raise RuntimeError("Workspace startup unavailable")


if __name__ == "__main__":
    try:
        ensure_server()
    except Exception:
        print("Workspace startup unavailable", file=sys.stderr)
        sys.exit(1)
