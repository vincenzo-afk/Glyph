# Glyph

Pluggable OCR service that turns images into structured, confidence-scored text — with a web UI, REST API, and swappable recognition engines.

## What it does

- Upload an image → get text back with per-line confidence and bounding boxes
- Annotated preview in the browser: boxes color-coded by confidence, click a box to jump to its line
- Three API modes: sync, async job polling, concurrent batch
- Export to JSON, TXT, CSV, PDF
- Preprocessing pipeline for skewed/noisy scans (deskew, denoise, threshold)
- Swap engines via one query param — add a new engine by implementing one method

## Engines

| Provider | Best for | Notes |
|---|---|---|
| Tesseract | Clean printed text | Default, CPU-only |
| EasyOCR | Handwriting, multi-language | Heavier, GPU-friendly |
| OpenAI (GPT-4o vision) | Hard/ambiguous images | Hosted, needs API key |

Check what's usable in your environment: `GET /api/v1/providers`

## Quickstart

```bash
git clone [https://github.com/](https://github.com/)<you>/glyph.git
cd glyph
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Tesseract binary
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr

uvicorn app.main:app --reload
# UI: http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

Or zero local setup:

```bash
docker compose up --build
```

## API

```bash
# Sync
curl -F "file=@samples/sample.png" http://localhost:8000/api/v1/ocr

# Async job
curl -F "file=@samples/sample.png" http://localhost:8000/api/v1/ocr/async
curl http://localhost:8000/api/v1/jobs/<job_id>

# Batch
curl -F "files=@a.png" -F "files=@b.png" http://localhost:8000/api/v1/ocr/batch
```

## Testing

```bash
pytest
```

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the provider plugin system and how to add a new engine.

## Known limits

- In-memory job store resets on restart (Redis is the documented upgrade path)
- Tesseract is weak on handwriting — use EasyOCR or the OpenAI provider for that
- No image persistence: images are processed in memory, never stored
