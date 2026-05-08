"""PaddleOCR-based text extraction with downscaling.

PaddleOCR is loaded lazily on first use to keep startup fast and to allow
unit tests to run without the heavy paddlepaddle dependency installed. The
model is held in a module-level singleton — initialising it twice would
double our memory footprint.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from chronolens.capture.screenshot import Screenshot

logger = logging.getLogger(__name__)

_ocr: Any | None = None
_ocr_unavailable = False


def _get_ocr() -> Any | None:
    """Return the cached PaddleOCR instance, or None if it cannot be loaded.

    The first call lazily imports paddleocr. If that fails (missing
    dependency, init error), we cache the failure and return None on every
    subsequent call so the capture loop keeps running without text.
    """
    global _ocr, _ocr_unavailable
    if _ocr is not None:
        return _ocr
    if _ocr_unavailable:
        return None
    try:
        from paddleocr import PaddleOCR

        _ocr = PaddleOCR(use_angle_cls=False, lang="en", use_gpu=False, show_log=False)
        logger.info("PaddleOCR initialised (CPU mode)")
    except Exception as exc:  # noqa: BLE001 — any failure → degraded mode
        _ocr_unavailable = True
        logger.warning("PaddleOCR unavailable, OCR disabled: %s", exc)
        return None
    return _ocr


def _downscale_to_width(screenshot: Screenshot, target_width: int) -> Any:
    """Convert raw BGRA bytes to a PIL Image scaled to `target_width`.

    Returns a numpy ndarray suitable for PaddleOCR. Lazy-imports PIL+numpy
    so test environments that don't have them stay green.
    """
    import numpy as np
    from PIL import Image

    img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.bgra, "raw", "BGRX")
    if screenshot.width > target_width:
        ratio = target_width / screenshot.width
        new_h = max(1, int(screenshot.height * ratio))
        img = img.resize((target_width, new_h), Image.Resampling.LANCZOS)
    return np.asarray(img)


def extract_text(screenshot: Screenshot, *, downscale_width: int = 1280) -> str:
    """Run PaddleOCR on the screenshot and return concatenated text.

    Returns an empty string if PaddleOCR is not available, the screenshot
    has no recognisable text, or the OCR call fails. The caller is expected
    to handle empty strings gracefully.
    """
    ocr = _get_ocr()
    if ocr is None:
        return ""
    try:
        arr = _downscale_to_width(screenshot, downscale_width)
        result = ocr.ocr(arr, cls=False)
    except Exception as exc:  # noqa: BLE001 — degraded mode rather than crash
        logger.warning("OCR extraction failed: %s", exc)
        return ""
    if not result or not result[0]:
        return ""
    return " ".join(line[1][0] for line in result[0] if line and line[1])


def reset_for_test() -> None:
    """Clear the cached OCR instance — used by tests that swap stubs in."""
    global _ocr, _ocr_unavailable
    _ocr = None
    _ocr_unavailable = False
