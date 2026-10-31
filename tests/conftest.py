"""Tiny synthetic corpus. Everything GPU-side (daemon, tesseract) is faked."""
import os
import sys
import types
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

KIT = ROOT.parent / "mc3-starter-kit"


def write_pdf(path, text):
    """Minimal single-page PDF whose extracted text we control."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(stream)).encode() + b">>stream\n" + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    out += b"".join(b"%010d 00000 n \n" % off for off in offsets)
    out += b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % xref
    path.write_bytes(out)


def write_docx(path, body_xml):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body>{body_xml}</w:body></w:document>")


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    import config
    idx = tmp_path / "index"
    idx.mkdir()
    monkeypatch.setattr(config, "INDEX_DIR", idx)
    monkeypatch.setattr(config, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(config, "CHUNKS_PATH", idx / "chunks.jsonl")
    monkeypatch.setattr(config, "MANIFEST_PATH", idx / "manifest.json")
    monkeypatch.setattr(config, "SOCKET_PATH", idx / "model.sock")
    monkeypatch.setattr(config, "DAEMON_LOG", idx / "daemon.log")
    monkeypatch.setattr(config, "LOCK_PATH", idx / "client.lock")
    return config


@pytest.fixture
def fake_tesseract(monkeypatch):
    """Files named *blurry* OCR to nothing; everything else to known text."""
    mod = types.ModuleType("pytesseract")
    mod.image_to_string = lambda img: "" if "blurry" in str(img.filename) else "OCR pin B14 THERM_ALERT"
    monkeypatch.setitem(sys.modules, "pytesseract", mod)


@pytest.fixture
def corpus(tmp_path, fake_tesseract):
    import openpyxl
    from PIL import Image
    c = tmp_path / "corpus"
    (c / "specs").mkdir(parents=True)
    (c / "empty_dir").mkdir()
    (c / "notes.txt").write_text("The default batch timeout of the ingest service is 180 seconds.\n")
    (c / "bugs.csv").write_text("ticket,fixed_in\nORR-1847,4.3.2\nORR-1802,4.3.1\n")
    write_docx(c / "roadmap.docx",
               "<w:p><w:r><w:t>TQ-60 enters customer sampling in Q3 FY27.</w:t></w:r></w:p>")
    wb = openpyxl.Workbook()
    wb.active.append(["part", "description"])
    wb.active.append(["ORR-FAN-2214-B", "Fan assembly, field replaceable"])
    wb.save(c / "parts.xlsx")
    write_pdf(c / "specs" / "sheet_r2.pdf", "Maximum junction temperature is 94 C")
    (c / "specs" / "sheet_r1_WITHDRAWN.txt").write_text("Maximum junction temperature is 105 C\n")
    (c / "old_SUPERSEDED.txt").write_text("Fan speed limit is 7000 rpm for this unit.\n")
    Image.new("RGB", (8, 8)).save(c / "specs" / "pinout.png")
    Image.new("RGB", (8, 8)).save(c / "specs" / "blurry.png")
    (c / "blob.dat").write_bytes(bytes(range(256)) * 4)
    (c / "zero.txt").write_bytes(b"")
    locked = c / "locked.txt"
    locked.write_text("restricted")
    os.chmod(locked, 0)
    yield c
    os.chmod(locked, 0o644)
