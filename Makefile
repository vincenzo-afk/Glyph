KIT ?= ../mc3-starter-kit
IMAGE ?= glyph:latest

.PHONY: fetch build test grade clean
fetch:
	./scripts/fetch_model.sh
build:
	docker build -t $(IMAGE) .
test:
	python3 -m pytest tests/ -v
grade:
	python3 scripts/grade_local.py $(KIT)/mc3-corpus
clean:
	rm -rf output index .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
