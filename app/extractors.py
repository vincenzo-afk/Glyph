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

