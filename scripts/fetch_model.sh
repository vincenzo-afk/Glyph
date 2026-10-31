#!/bin/sh
# Run at BUILD time, when the network is open. Ships weights inside the image.
set -e
mkdir -p models
# Newer huggingface_hub replaces huggingface-cli with hf.
if command -v hf >/dev/null 2>&1; then DL="hf download"; else DL="huggingface-cli download"; fi
$DL Qwen/Qwen2.5-VL-7B-Instruct --local-dir models/qwen2_5-vl-7b-instruct
echo "models/ ready ($(du -sh models | cut -f1))"
