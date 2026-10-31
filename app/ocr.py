"""Image -> text via tesseract OCR, plus a vision-model pass at index time."""
from __future__ import annotations


def ocr_image(p, rel, cfg):
    """Local, dependency-light OCR. Never raises."""
    from extractors import Extracted, _mark_stale
    try:
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(str(p)))
        if text.strip():
            return Extracted(rel, True, text=text, extra={"source": "ocr"},
                             stale=_mark_stale(rel, text, cfg.STALE_MARKERS))
        return Extracted(rel, False, error="ocr produced no text")
    except Exception as e:
        return Extracted(rel, False, error=f"ocr: {type(e).__name__}")
