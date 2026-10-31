"""GPU-resident model behind a unix socket. Started by --index, stays alive
across the ten per-question processes. This is what keeps each --query under
30 seconds.

Wire protocol: one JSON line per request, one JSON line per response.
"""
from __future__ import annotations
import errno
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config as cfg  # noqa: E402

try:
    import fcntl
except ImportError:
    fcntl = None

_pipe = None


def _load_pipe():
    global _pipe
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    model_id = cfg.MODEL_DIR.as_posix()
    proc = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, torch_dtype=torch.bfloat16, device_map="cuda",
    )
    model.eval()
    _pipe = (proc, model)
    return proc, model


