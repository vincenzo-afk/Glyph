"""Thin client used by per-question processes (and the index-time vision pass).

The harness starts a NEW PROCESS per question, so nothing here may load the
model synchronously unless the daemon is genuinely down.
"""
from __future__ import annotations
import contextlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config as cfg  # noqa: E402

try:
    import fcntl
except ImportError:         # non-POSIX dev box: serialization is best-effort
    fcntl = None

# The daemon is genuinely gone only in these cases. A socket.timeout means it
# is alive and mid-generation: respawning then would put two models on one GPU.
DAEMON_DOWN = (FileNotFoundError, ConnectionError)
_RETRY = (FileNotFoundError, ConnectionRefusedError)


def use_groq() -> bool:
    return os.environ.get("GLYPH_BACKEND", "local") == "groq"


def _request(payload: dict, wait: float, timeout: float = None) -> dict:
    deadline = time.time() + wait
    while True:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.settimeout(timeout or cfg.SOCKET_TIMEOUT)
            s.connect(str(cfg.SOCKET_PATH))
            s.sendall((json.dumps(payload) + "\n").encode())
            with s.makefile("rb") as fh:
                data = fh.readline()
            if not data:
                raise ConnectionResetError("daemon closed the connection")
            resp = json.loads(data)
            if resp.get("ok"):
                return resp
            raise RuntimeError(resp.get("error", "daemon error"))
        except _RETRY:
            if time.time() > deadline:
                raise
            time.sleep(0.5)
        finally:
            s.close()


def _spawn_daemon():
    cfg.DAEMON_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg.DAEMON_LOG, "ab") as log:
        return subprocess.Popen([sys.executable, str(HERE / "daemon.py")],
                                stdout=log, stderr=log, start_new_session=True,
                                cwd=str(HERE))


def ensure_daemon(wait: float) -> bool:
    """Idempotent: reuse a live daemon, else spawn one and wait for /ping."""
    if use_groq():
        return True
    try:
        _request({"op": "ping"}, wait=0.0)
        return True
    except Exception:
        pass
    proc = _spawn_daemon()
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            _request({"op": "ping"}, wait=0.0)
            return True
        except Exception:
            if proc.poll() is not None:     # died: OOM, bad model dir, or lost the lock race
                try:
                    _request({"op": "ping"}, wait=1.0)   # a sibling daemon may own the socket
                    return True
                except Exception:
                    return False
            time.sleep(0.5)
    return False


@contextlib.contextmanager
def _serialized():
    """Cross-process lock so parallel harness invocations cannot race the daemon."""
    if fcntl is None:
        yield
        return
    try:
        cfg.LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fh = open(cfg.LOCK_PATH, "a")
    except OSError:
        yield
        return
    with fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)

