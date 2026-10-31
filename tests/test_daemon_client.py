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


