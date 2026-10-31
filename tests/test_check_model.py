import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_model.py"


@pytest.fixture(scope="module")
def check():
    spec = importlib.util.spec_from_file_location("check_model", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def complete(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    (d / "config.json").write_text("{}")
    (d / "tokenizer.json").write_text("{}")
    (d / "preprocessor_config.json").write_text("{}")
    (d / "model-00001-of-00002.safetensors").write_bytes(b"w")


def test_complete_model_has_no_problems(check, tmp_path):
    complete(tmp_path / "m")
    assert check.missing(tmp_path / "m") == []


def test_missing_directory(check, tmp_path):
    assert check.missing(tmp_path / "nope")[0].startswith("directory")


def test_missing_weights_reported(check, tmp_path):
    complete(tmp_path / "m")
    (tmp_path / "m" / "model-00001-of-00002.safetensors").unlink()
    assert "*.safetensors" in check.missing(tmp_path / "m")


def test_empty_shard_reported(check, tmp_path):
    complete(tmp_path / "m")
    (tmp_path / "m" / "model-00001-of-00002.safetensors").write_bytes(b"")
    assert any("empty weight shard" in p for p in check.missing(tmp_path / "m"))


def test_either_tokenizer_file_is_enough(check, tmp_path):
    complete(tmp_path / "m")
    (tmp_path / "m" / "tokenizer.json").unlink()
    (tmp_path / "m" / "vocab.json").write_text("{}")
    assert check.missing(tmp_path / "m") == []


def test_main_exit_codes(check, tmp_path, capsys):
    assert check.main(["x", str(tmp_path / "nope")]) == 1
    complete(tmp_path / "m")
    assert check.main(["x", str(tmp_path / "m")]) == 0
    assert "model complete" in capsys.readouterr().out
