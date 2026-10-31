KIT ?= ../mc3-starter-kit
IMAGE ?= glyph:latest

.PHONY: help fetch check-model build test grade clean
help:
	@echo "fetch        download Qwen2.5-VL-7B into models/ (build time, needs network)"
	@echo "check-model  fail if models/ is incomplete"
	@echo "build        check-model, then docker build"
	@echo "test         run the test suite (no GPU, Docker or tesseract needed)"
	@echo "grade        score the kit's sample questions (needs GPU or MC3_BACKEND=groq)"
	@echo "clean        remove generated output, indexes and caches"
fetch:
	./scripts/fetch_model.sh
check-model:
	python3 scripts/check_model.py models/qwen2_5-vl-7b-instruct
build: check-model
	docker build -t $(IMAGE) .
test:
	python3 -m pytest tests/ -v
grade:
	python3 scripts/grade_local.py $(KIT)/mc3-corpus
clean:
	rm -rf output index .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
