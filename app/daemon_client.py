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

