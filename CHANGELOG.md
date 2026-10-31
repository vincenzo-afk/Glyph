# Changelog

## Unreleased

### Fixed
- The GPU daemon starts before the index walk, so images get vision descriptions.
- Answers are checked against extracted chunk text, so PDF, DOCX and XLSX answers
  are no longer refused by reading the raw binary.
- Images are described by the vision model even when OCR finds no text.
- The default model path matches `fetch_model.sh`; the daemon refuses to start on
  an incomplete model directory.
- Tool-call JSON is parsed from the first valid object, not a greedy regex.
- A timeout from the daemon no longer respawns it; only a missing socket does.
- Unreadable, empty, oversized and misdetected files are recorded per file.
- Stale markers match inside filenames with underscores, and a line saying a file
  "supersedes" another no longer marks the newer file as stale.
- Answer values match whole tokens only, so `94` is not found inside `1940`.
- A failed query writes a refusal instead of no output.
- The grader's normalisation handles `94°C`.

### Added
- Entity hop for multi-hop questions that name an identifier not in the question.
- Citation necessity: bridge files are kept, redundant files are dropped.
- Cross-process lock around daemon requests; single daemon per index directory.
- `GLYPH_BACKEND=groq` for development without a GPU.
- `scripts/check_model.py` and `make check-model`; `make build` depends on it.
- Test suite, CI workflow, and documentation under `docs/`.

### Not verified
- Anything that needs the AMD GPU, Docker, or the network: model load, VRAM use,
  the 30 s budget, the image size, and running without `DAC_OVERRIDE`.
