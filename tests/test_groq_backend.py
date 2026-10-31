import io
import json
import urllib.error

import pytest

import groq_backend


class FakeResp:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def ok_body(text):
    return {"choices": [{"message": {"content": text}}]}


def http_error(code, retry_after=None):
    headers = {"retry-after": retry_after} if retry_after else {}
    return urllib.error.HTTPError("u", code, "x", headers, io.BytesIO(b"nope"))


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(groq_backend.time, "sleep", lambda s: None)


def test_returns_message_content(key, monkeypatch):
    monkeypatch.setattr(groq_backend.urllib.request, "urlopen",
                        lambda req, timeout: FakeResp(ok_body('{"answer": "94"}')))
    assert groq_backend._chat({"model": "m"}, 5.0) == '{"answer": "94"}'


def test_retries_on_429_then_succeeds(key, monkeypatch):
    calls = []

    def urlopen(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise http_error(429, retry_after="1")
        return FakeResp(ok_body("done"))

    monkeypatch.setattr(groq_backend.urllib.request, "urlopen", urlopen)
    assert groq_backend._chat({"model": "m"}, 30.0) == "done"
    assert len(calls) == 2


def test_client_error_is_not_retried(key, monkeypatch):
    calls = []

    def urlopen(req, timeout):
        calls.append(1)
        raise http_error(400)

    monkeypatch.setattr(groq_backend.urllib.request, "urlopen", urlopen)
    with pytest.raises(RuntimeError, match="groq 400"):
        groq_backend._chat({"model": "m"}, 30.0)
    assert len(calls) == 1


def test_gives_up_when_retry_would_exceed_budget(key, monkeypatch):
    monkeypatch.setattr(groq_backend.urllib.request, "urlopen",
                        lambda req, timeout: (_ for _ in ()).throw(http_error(429, "999")))
    with pytest.raises(RuntimeError, match="out of budget"):
        groq_backend._chat({"model": "m"}, 5.0)


def test_missing_key_is_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(groq_backend, "Path", lambda p: tmp_path / "x" / "y")
    with pytest.raises(RuntimeError, match="GROQ_API_KEY is not set"):
        groq_backend._key()


def test_key_read_from_dotenv(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OTHER=1\nGROQ_API_KEY=from-file\n")
    fake_root = tmp_path / "app" / "groq_backend.py"
    monkeypatch.setattr(groq_backend, "__file__", str(fake_root))
    assert groq_backend._key() == "from-file"
