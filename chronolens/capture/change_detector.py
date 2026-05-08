"""Detect whether the screen has meaningfully changed between ticks.

Cheap fast-path: window title / process / URL string comparison.
Slow path: perceptual hash (dhash) of the screenshot, compared via Hamming
distance to the previous hash. Both paths are tunable via settings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chronolens.capture.screenshot import Screenshot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChangeState:
    """Mutable state carried between change-detection invocations."""

    title: str = ""
    process: str = ""
    url: str = ""
    phash: str = ""


@dataclass(frozen=True, slots=True)
class ChangeResult:
    """Outcome of a single change-detection check."""

    changed: bool
    reason: str  # "title", "process", "url", "phash", "none"
    phash: str


def _dhash_from_screenshot(screenshot: Screenshot, hash_size: int = 8) -> str:
    """Compute a difference-hash of the screenshot's grayscale resize.

    We avoid the heavy `imagehash` import here; PIL alone is enough to do a
    `(hash_size+1) x hash_size` grayscale resize and produce a 64-bit hex
    string that compares with Hamming distance.
    """
    from PIL import Image

    img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.bgra, "raw", "BGRX")
    img = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(img.tobytes())
    bits = 0
    for row in range(hash_size):
        offset = row * (hash_size + 1)
        for col in range(hash_size):
            bits = (bits << 1) | (1 if pixels[offset + col] > pixels[offset + col + 1] else 0)
    return f"{bits:0{hash_size * hash_size // 4}x}"


def hamming_distance(a: str, b: str) -> int:
    """Hamming distance between two equal-length hex hashes."""
    if not a or not b or len(a) != len(b):
        return 64  # treat mismatched/missing hashes as maximally different
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def detect_change(
    screenshot: Screenshot | None,
    title: str,
    process: str,
    url: str,
    state: ChangeState,
    *,
    phash_threshold: int = 5,
) -> ChangeResult:
    """Decide whether the screen changed since the previous tick.

    Updates `state` in place with the latest title/process/url/phash so the
    caller doesn't have to. Returns a `ChangeResult` describing the outcome.

    Args:
        screenshot: Current screenshot, or None if capture failed (treated
            as "no slow-path check possible").
        title: Active window title.
        process: Active process name.
        url: Browser URL (empty string when no browser context).
        state: Mutable state from the previous tick.
        phash_threshold: Hamming distance above which the screen is
            considered changed.
    """
    if title != state.title:
        state.title = title
        state.process = process
        state.url = url
        if screenshot is not None:
            state.phash = _dhash_from_screenshot(screenshot)
        return ChangeResult(changed=True, reason="title", phash=state.phash)

    if process != state.process:
        state.process = process
        if screenshot is not None:
            state.phash = _dhash_from_screenshot(screenshot)
        return ChangeResult(changed=True, reason="process", phash=state.phash)

    if url and url != state.url:
        state.url = url
        if screenshot is not None:
            state.phash = _dhash_from_screenshot(screenshot)
        return ChangeResult(changed=True, reason="url", phash=state.phash)

    if screenshot is None:
        return ChangeResult(changed=False, reason="none", phash=state.phash)

    new_hash = _dhash_from_screenshot(screenshot)
    distance = hamming_distance(new_hash, state.phash)
    if distance > phash_threshold:
        state.phash = new_hash
        return ChangeResult(changed=True, reason="phash", phash=new_hash)

    return ChangeResult(changed=False, reason="none", phash=state.phash)
