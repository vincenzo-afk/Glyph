import sys
import types

from ocr import ocr_image


class Img:
    filename = "scan.png"


def fake_tesseract(monkeypatch, text=None, exc=None):
    mod = types.ModuleType("pytesseract")

    def image_to_string(img):
        if exc:
            raise exc
        return text

    mod.image_to_string = image_to_string
    monkeypatch.setitem(sys.modules, "pytesseract", mod)


def test_ocr_text_is_extracted(tmp_path, cfg, monkeypatch):
    p = tmp_path / "scan.png"
    fake_tesseract(monkeypatch, text="REV-C2")
    monkeypatch.setattr("PIL.Image.open", lambda path: Img())
    r = ocr_image(p, "scan.png", cfg)
    assert r.ok and r.text == "REV-C2"


def test_blank_ocr_is_a_recorded_failure_not_an_exception(tmp_path, cfg, monkeypatch):
    p = tmp_path / "blur.png"
    fake_tesseract(monkeypatch, text="   ")
    monkeypatch.setattr("PIL.Image.open", lambda path: Img())
    r = ocr_image(p, "blur.png", cfg)
    assert not r.ok and r.error == "ocr produced no text"


def test_missing_tesseract_binary_is_a_recorded_failure(tmp_path, cfg, monkeypatch):
    p = tmp_path / "x.png"
    fake_tesseract(monkeypatch, exc=OSError("tesseract not installed"))
    monkeypatch.setattr("PIL.Image.open", lambda path: Img())
    r = ocr_image(p, "x.png", cfg)
    assert not r.ok and r.error.startswith("ocr: ")
