# Mandated base (checked by layer identity). Ships torch + PIL for ROCm.
FROM rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0

# OCR for the image-only answers (png/jpg).
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Application code.
COPY app/ /app/

# WEIGHTS SHIP IN THE IMAGE. At evaluation there is NO network; anything
# downloaded at runtime hangs and scores zero. Populate models/ BEFORE build:
#   ./scripts/fetch_model.sh
COPY models/ /models/
ENV GLYPH_MODEL=/models/qwen2_5-vl-7b-instruct
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1

# Contract paths; harness copies the graded corpus to /app/corpus.
RUN mkdir -p /app/corpus /app/output /app/index

# No server, no port. The container only has to stay up to be exec'd into.
CMD ["sleep", "infinity"]
