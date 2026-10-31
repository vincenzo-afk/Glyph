# glyph -- Mini-Challenge 3 submission

Containerized RAG over a mixed-document corpus (pdf, docx, xlsx, csv, txt,
log, py, png, jpg) that answers value-only questions and returns the exact
corpus-relative files each answer comes from.

## Pipeline
1. `--index`  : start the GPU daemon (Qwen2.5-VL-7B, bf16, unix socket) and wait
                for it -> resilient per-file parse -> chunk -> OCR + vision
                descriptions for ALL images -> persist. The daemon stays resident.
2. `--query`  : BM25 + entity hop (ticket IDs etc.) -> excerpts tagged by file ->
                daemon extracts a value + files -> postprocess checks the value
                against retrieved chunk text, strips units, demotes WITHDRAWN
                docs, keeps only necessary citations, or refuses.

## Layout
`app/` is copied to `/app`; `tests/` runs without GPU, Docker or tesseract;
`scripts/` holds the fetch, grade and full-check scripts.

## Build & test (Linux, AMD GPU, Docker)
    make test                           # no GPU needed
    ../mc3-starter-kit/setup.sh         # once: empty dir + chmod 000 case
    make fetch                          # build-time only; eval has NO network
    make build                          # system dep tesseract-ocr is in the Dockerfile
    python3 ../mc3-starter-kit/selfcheck.py glyph:latest ../mc3-starter-kit/mc3-corpus
    make grade                          # needs the GPU; shuts its daemon down afterwards

Test the unreadable file for real with `docker run --cap-drop DAC_OVERRIDE ...`.

## Environment
`GLYPH_OUTPUT_DIR` (`/app/output`), `GLYPH_INDEX_DIR` (`/app/index`),
`GLYPH_MODEL` (`/models/qwen2_5-vl-7b-instruct`).

## Development without a GPU
`GLYPH_BACKEND=groq` sends model calls to Groq, reading `GROQ_API_KEY` from the
environment or an untracked `.env`:

    GLYPH_BACKEND=groq python scripts/grade_local.py ../mc3-starter-kit/mc3-corpus

