"""Per-file-type text extraction. Every failure is local to its file."""
from __future__ import annotations
import csv
import html
import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

MAX_BYTES = 50 * 1024 * 1024     # refreshed from cfg.MAX_FILE_BYTES in extract_file


@dataclass
class Extracted:
    path: str
    ok: bool
    text: str = ""
    error: str = ""
    stale: bool = False
    extra: dict = field(default_factory=dict)


def _decode(raw: bytes) -> str:
    """utf-8 / utf-16 (BOM) / cp1252 fallback; never raises."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", "replace")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", "replace")


def _read_capped(p: Path, cap: int) -> bytes:
    with open(p, "rb") as fh:
        return fh.read(cap)


def _looks_textual(raw: bytes) -> bool:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf")):
        return True
    printable = sum(1 for b in raw if 32 <= b < 127 or b in (9, 10, 13) or b >= 0xA0)
    return bool(raw) and b"\x00" not in raw and printable / len(raw) > 0.85


def _mark_stale(path: str, text: str, markers) -> bool:
    # Only the NAME and the first lines of the file count: a current doc may
    # legitimately mention that an OLD revision was withdrawn inside its body
    # (revision history), and must not be flagged itself.
    # A line saying this doc SUPERSEDES another describes the other doc.
    lines = [ln for ln in text.split("\n")[:3] if "SUPERSEDES" not in ln.upper()]
    h = (path + "\n" + "\n".join(lines)).upper()
    # Not \b: "_" is a word char, so \bWITHDRAWN\b misses r1_WITHDRAWN.pdf.
    return any(re.search(r"(?<![A-Z])" + m + r"(?![A-Z])", h) for m in markers)


def _read_pdf(p: Path, rel: str, markers) -> Extracted:
    try:
        r = PdfReader(str(p))
        if r.is_encrypted:
            try:
                r.decrypt("")
            except Exception:
                return Extracted(rel, False, error="encrypted pdf")
        text = " ".join((pg.extract_text() or "") for pg in r.pages)
        if not text.strip():
            return Extracted(rel, False, error="no extractable text (scanned/encrypted)")
        return Extracted(rel, True, text=text,
                         stale=_mark_stale(rel, text, markers))
    except Exception as e:  # PasswordError lands here too
        return Extracted(rel, False, error=f"pdf: {type(e).__name__}")


def _read_docx(p: Path, rel: str, markers) -> Extracted:
    try:
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        # cells -> " | ", rows/paragraphs -> newline (tables-only docs stay readable)
        xml = xml.replace("</w:tc>", " | ").replace("</w:p>", "\n").replace("</w:tr>", "\n")
        text = html.unescape(re.sub(r"<[^>]+>", " ", xml))
        text = re.sub(r"[ \t]+", " ", text)
        if not text.strip(" |\n"):
            return Extracted(rel, False, error="empty docx body")
        return Extracted(rel, True, text=text,
                         stale=_mark_stale(rel, text, markers))
    except Exception as e:
        return Extracted(rel, False, error=f"docx: {type(e).__name__}")


def _read_xlsx(p: Path, rel: str, markers) -> Extracted:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
        lines = []
        for ws in wb.worksheets:
            lines.append(f"[sheet {ws.title}]")
            for row in ws.iter_rows(values_only=True):
                cells = ["" if c is None else str(c) for c in row]
                if any(cells):
                    lines.append(" | ".join(cells))
        wb.close()
        text = "\n".join(lines)
        return Extracted(rel, True, text=text,
                         stale=_mark_stale(rel, text, markers))
    except Exception as e:
        return Extracted(rel, False, error=f"xlsx: {type(e).__name__}")


def _read_csv(p: Path, rel: str, markers) -> Extracted:
    try:
        text = _decode(_read_capped(p, MAX_BYTES))
        try:
            rows = list(csv.reader(io.StringIO(text)))
            if rows and len(rows[0]) > 1:
                header = rows[0]
                lines = [" | ".join(header)]
                for r in rows[1:]:
                    cells = [f"{h}: {v}" if v else h for h, v in zip(header, r)]
                    cells += r[len(header):]        # ragged rows keep their extra cells
                    lines.append(" | ".join(cells))
                text = "\n".join(lines)
        except Exception:
            pass
        return Extracted(rel, True, text=text,
                         stale=_mark_stale(rel, text, markers))
    except Exception as e:
        return Extracted(rel, False, error=f"csv: {type(e).__name__}")

