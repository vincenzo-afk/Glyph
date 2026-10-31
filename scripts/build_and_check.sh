#!/bin/sh
# Full pipeline: fetch weights -> build -> contract selfcheck -> local grade.
set -e
./scripts/fetch_model.sh
docker build -t glyph:latest .
python3 ../mc3-starter-kit/selfcheck.py glyph:latest ../mc3-starter-kit/mc3-corpus
python3 scripts/grade_local.py ../mc3-starter-kit/mc3-corpus
