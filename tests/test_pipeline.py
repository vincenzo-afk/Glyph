"""End-to-end through app.main() with the GPU daemon faked: --index, then --query."""
import json
import sys

import pytest

import app as app_mod
import daemon_client
from conftest import KIT


@pytest.fixture
def daemon_up(monkeypatch):
    calls = []
    monkeypatch.setattr(daemon_client, "ensure_daemon", lambda wait: calls.append("up") or True)
    monkeypatch.setattr(daemon_client, "_request", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(daemon_client, "vision_describe", lambda p: "")
    return calls


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["app.py", *argv])
    return app_mod.main()


def query(monkeypatch, cfg, corpus, q, model_reply=None):
    seen = {}
    def ask(query, context):
        seen["context"] = context
        return model_reply
    monkeypatch.setattr(daemon_client, "ask", ask)
    assert run(monkeypatch, "--corpus", str(corpus), "--query-id", "q1", "--query", q) == 0
    return json.loads((cfg.OUTPUT_DIR / "q1_output.json").read_text(encoding="utf-8")), seen


def test_daemon_is_up_before_the_vision_pass(tmp_path, cfg, monkeypatch):
    # Regression P0-1.
    order = []
    monkeypatch.setattr(daemon_client, "ensure_daemon", lambda w: order.append("daemon") or True)
    monkeypatch.setattr(daemon_client, "_request", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(app_mod, "build_index", lambda c, f: order.append("index"))
    run(monkeypatch, "--index", str(tmp_path))
    assert order == ["daemon", "index"]

