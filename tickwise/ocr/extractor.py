"""RapidOCR-based text extraction with downscaling.

RapidOCR is a fork of PaddleOCR that runs on ONNX Runtime instead of
PaddlePaddle — same recognition quality, ~50 MB instead of 250+ MB,
and no native deps that break under PyInstaller. The model is loaded
lazily on first use to keep startup fast.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tickwise.capture.screenshot import Screenshot

logger = logging.getLogger(__name__)

_ocr: Any | None = None
_ocr_unavailable = False


def is_available() -> bool:
    """Cheap probe — returns True iff OCR is initialised or initialisable."""
    if _ocr is not None:
        return True
    if _ocr_unavailable:
        return False
    try:
        import rapidocr_onnxruntime  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _get_ocr() -> Any | None:
    """Return the cached RapidOCR instance, or None if it cannot be loaded.

    First call lazily imports rapidocr_onnxruntime. Failure is cached so
    the capture loop keeps running without text and we don't pay the
    import penalty every tick.
    """
    global _ocr, _ocr_unavailable
    if _ocr is not None:
        return _ocr
    if _ocr_unavailable:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR

        _ocr = RapidOCR()
        logger.info("RapidOCR initialised (ONNX, CPU)")
    except Exception as exc:  # noqa: BLE001
        _ocr_unavailable = True
        logger.warning("OCR unavailable, disabled: %s", exc)
        return None
    return _ocr


def _downscale_to_width(screenshot: Screenshot, target_width: int) -> Any:
    """Convert raw BGRA bytes to a numpy array scaled to `target_width`.

    Returns an ndarray suitable for RapidOCR (`H × W × 3`, BGR or RGB).
    Lazy-imports PIL+numpy so test environments without them stay green.
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
    """Run OCR on the screenshot and return concatenated text.

    Returns an empty string if OCR is unavailable, the screenshot has
    no recognisable text, or the OCR call fails. Caller handles empty.
    """
    ocr = _get_ocr()
    if ocr is None:
        return ""
    try:
        arr = _downscale_to_width(screenshot, downscale_width)
        result, _elapse = ocr(arr)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR extraction failed: %s", exc)
        return ""
    if not result:
        return ""
    # RapidOCR returns: [[bbox, text, score], ...]
    return " ".join(line[1] for line in result if line and len(line) >= 2 and line[1])


def reset_for_test() -> None:
    """Clear the cached OCR instance — used by tests that swap stubs in."""
    global _ocr, _ocr_unavailable
    _ocr = None
    _ocr_unavailable = False
