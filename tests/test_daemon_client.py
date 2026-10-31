import errno
import socket
import sys
import types

import pytest

import config
import daemon
import daemon_client


class Spawn:
    def __init__(self, monkeypatch):
        self.calls = 0
        monkeypatch.setattr(daemon_client, "_spawn_daemon", self)

    def __call__(self):
        self.calls += 1


def scripted(monkeypatch, *outcomes):
    seq = list(outcomes)
    def fake(payload, wait, timeout=None):
        o = seq.pop(0)
        if isinstance(o, Exception):
            raise o
        return o
    monkeypatch.setattr(daemon_client, "_request", fake)


@pytest.mark.parametrize("exc", [ConnectionRefusedError(), FileNotFoundError(), ConnectionResetError()])
def test_respawns_when_daemon_is_gone(monkeypatch, exc):
    spawn = Spawn(monkeypatch)
    scripted(monkeypatch, exc, {"text": "ok"})
    assert daemon_client.ask("q", "c") == "ok"
    assert spawn.calls == 1


def test_no_respawn_on_timeout(monkeypatch):
    # Regression P1-1: a timeout means alive and busy.
    spawn = Spawn(monkeypatch)
    scripted(monkeypatch, socket.timeout())
    with pytest.raises(socket.timeout):
        daemon_client.ask("q", "c")
    assert spawn.calls == 0


def test_vision_failure_is_empty(monkeypatch):
    scripted(monkeypatch, ConnectionRefusedError())
    assert daemon_client.vision_describe("x.png") == ""


def test_vision_gets_its_own_timeout(monkeypatch):
    seen = {}
    def fake(payload, wait, timeout=None):
        seen["timeout"] = timeout
        return {"text": "t"}
    monkeypatch.setattr(daemon_client, "_request", fake)
    daemon_client.vision_describe("x.png")
    assert seen["timeout"] == config.VISION_TIMEOUT > config.SOCKET_TIMEOUT


def test_spawn_creates_log_parent(tmp_path, monkeypatch):
    # Regression P1-4.
    monkeypatch.setattr(config, "DAEMON_LOG", tmp_path / "deep" / "er" / "d.log")
    monkeypatch.setattr(daemon_client.subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setitem(__import__("os").environ, "X", "1")
    try:
        daemon_client._spawn_daemon()
    except Exception as e:
        pytest.fail(str(e))
    assert config.DAEMON_LOG.exists()


def test_ensure_daemon_reuses_live_daemon(monkeypatch):
    spawn = Spawn(monkeypatch)
    scripted(monkeypatch, {"ok": True})
    assert daemon_client.ensure_daemon(1.0) is True
    assert spawn.calls == 0


def test_ensure_daemon_fails_fast_if_it_dies(monkeypatch):
    class Dead:
        def poll(self):
            return 1
    monkeypatch.setattr(daemon_client, "_spawn_daemon", lambda: Dead())
    def refuse(payload, wait, timeout=None):
        raise ConnectionRefusedError
    monkeypatch.setattr(daemon_client, "_request", refuse)
    assert daemon_client.ensure_daemon(60.0) is False


def test_socket_timeout_budget():
    assert 25 < config.SOCKET_TIMEOUT < 30


class FakeSrv:
    """accept(): EINTR, then a generic failure that ends the loop."""
    def __init__(self):
        self.errors = [OSError(errno.EINTR, "x"), OSError(errno.EBADF, "y")]
        self.accepts = 0
    def bind(self, p): pass
    def listen(self, n): pass
    def accept(self):
        self.accepts += 1
        raise self.errors.pop(0)


def test_serve_survives_eintr(cfg, tmp_path, monkeypatch):
    # Regression P1-3. AF_UNIX is absent on Windows, hence the fake module.
    model = tmp_path / "m"
    model.mkdir()
    (model / "config.json").write_text("{}")
    monkeypatch.setattr(config, "MODEL_DIR", model)
    monkeypatch.setattr(daemon, "_load_pipe", lambda: None)
    srv = FakeSrv()
    monkeypatch.setitem(sys.modules, "socket", types.SimpleNamespace(
        AF_UNIX=1, SOCK_STREAM=1, socket=lambda *a: srv))
    daemon.serve()
    assert srv.accepts == 2         # EINTR retried; EBADF ended the loop

