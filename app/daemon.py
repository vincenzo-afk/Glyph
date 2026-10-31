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


def generate(query: str, context: str, max_new: int = 96) -> dict:
    import torch
    from prompts import EXTRACTION_PROMPT, MODEL_SYSTEM
    proc, model = _pipe if _pipe else _load_pipe()
    prompt = EXTRACTION_PROMPT.format(
        query=query, context=context, max_c=cfg.MAX_CITATIONS)
    msgs = [{"role": "system", "content": MODEL_SYSTEM},
            {"role": "user", "content": prompt}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = proc(text=[text], return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new, do_sample=False,
                             temperature=None, top_p=None, top_k=None)
    gen = proc.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return {"text": gen.strip()}


def vision_describe(image_path: str) -> str:
    import torch
    from PIL import Image
    from prompts import VISION_PROMPT
    proc, model = _pipe if _pipe else _load_pipe()
    msgs = [{"role": "user", "content": [
        {"type": "image"}, {"type": "text", "text": VISION_PROMPT}]}]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = proc(text=[text], images=[Image.open(image_path).convert("RGB")],
                  return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=512, do_sample=False,
                             temperature=None, top_p=None, top_k=None)
    return proc.decode(out[0][inputs["input_ids"].shape[1]:],
                       skip_special_tokens=True).strip()


def _single_instance():
    """Hold an exclusive lock for the daemon's lifetime: a second daemon on the
    same index dir exits instead of fighting over the GPU and the socket."""
    if fcntl is None:
        return None
    fh = open(cfg.DAEMON_LOCK_PATH, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("another daemon already owns " + str(cfg.DAEMON_LOCK_PATH))
    return fh


def _log(msg: str) -> None:
    try:
        with open(cfg.DAEMON_LOG, "a") as log:
            log.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except OSError:
        pass                        # full/unwritable log must never kill the daemon


def serve():
    import socket
    cfg.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if not (cfg.MODEL_DIR / "config.json").exists():
        raise SystemExit(f"model not found: {cfg.MODEL_DIR}/config.json "
                         "(set GLYPH_MODEL; see scripts/fetch_model.sh)")
    lock = _single_instance()       # noqa: F841  (kept referenced for process lifetime)
    if cfg.SOCKET_PATH.exists():
        cfg.SOCKET_PATH.unlink()
    _load_pipe()                      # model is on the GPU before we listen
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(cfg.SOCKET_PATH))
    srv.listen(4)
    _log("daemon up")
    running = True
    while running:
        try:
            conn, _ = srv.accept()
        except OSError as e:
            if e.errno in (errno.EINTR, errno.EAGAIN):
                continue
            _log(f"accept failed: {e}")
            break
        with conn:
            conn.settimeout(60.0)   # a client that connects and goes silent must not wedge us
            try:
                req = json.loads(conn.makefile("rb").readline())
                if req.get("op") == "ping":
                    resp = {"ok": True}
                elif req.get("op") == "shutdown":
                    resp, running = {"ok": True}, False
                elif req.get("op") == "vision":
                    resp = {"ok": True, "text": vision_describe(req["path"])}
                else:
                    resp = {"ok": True, **generate(req["query"], req["context"])}
            except Exception as e:
                resp = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            try:
                conn.sendall((json.dumps(resp) + "\n").encode())
            except OSError:
                pass
    try:
        cfg.SOCKET_PATH.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    serve()
