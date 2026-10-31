"""Central configuration. Everything overridable via environment."""
from __future__ import annotations
import os
from pathlib import Path

OUTPUT_DIR = Path(os.environ.get("GLYPH_OUTPUT_DIR", "/app/output"))
INDEX_DIR = Path(os.environ.get("GLYPH_INDEX_DIR", "/app/index"))
# fetch_model.sh downloads into models/qwen2_5-vl-7b-instruct, which the
# Dockerfile copies to /models/.
MODEL_DIR = Path(os.environ.get("GLYPH_MODEL", "/models/qwen2_5-vl-7b-instruct"))
SOCKET_PATH = INDEX_DIR / "model.sock"
DAEMON_LOG = INDEX_DIR / "daemon.log"
LOCK_PATH = INDEX_DIR / "client.lock"          # serializes ask() across processes
DAEMON_LOCK_PATH = INDEX_DIR / "daemon.lock"   # one daemon per index dir
MANIFEST_PATH = INDEX_DIR / "manifest.json"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"

CHUNK_TARGET = 450        # chars per chunk
CHUNK_OVERLAP = 80
TOP_K = 8                 # chunks fed to the model
MAX_CITATIONS = 3
MAX_FILE_BYTES = 50 * 1024 * 1024   # bigger files are recorded as errors (text is truncated)
MAX_QUERY_CHARS = 2000
PRUNE_REDUNDANT = True    # cite one file when several each contain the answer
SOCKET_TIMEOUT = 27.0     # seconds, inside the 30s per-query budget (cold KV cache ~24s)
VISION_TIMEOUT = 120.0    # seconds per image at index time; not on the per-query clock
DAEMON_WAIT = 240.0      # seconds a client will wait for a cold daemon

TEXT_SUFFIXES = {".txt", ".log", ".csv", ".py", ".md", ".json", ".cfg",
                 ".ini", ".yaml", ".yml", ".xml", ".html", ".sh", ".c", ".h"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
STALE_MARKERS = ("WITHDRAWN", "SUPERSEDED", "OBSOLETE", "DEPRECATED")
