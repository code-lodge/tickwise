"""Unit tests for chronolens.capture.change_detector."""

from __future__ import annotations

import pytest

from chronolens.capture.change_detector import (
    ChangeState,
    detect_change,
    hamming_distance,
)
from chronolens.capture.screenshot import Screenshot


def _solid_screenshot(value: int = 0) -> Screenshot:
    """Build a 64x64 BGRX screenshot filled with `value` per channel."""
    pixels = bytes([value, value, value, 255]) * (64 * 64)
    return Screenshot(width=64, height=64, bgra=pixels)


def _checker_screenshot() -> Screenshot:
    """Build a 64x64 black/white checker screenshot."""
    rows: list[bytes] = []
    for y in range(64):
        row = bytearray()
        for x in range(64):
            v = 255 if ((x // 8) + (y // 8)) % 2 == 0 else 0
            row += bytes([v, v, v, 255])
        rows.append(bytes(row))
    return Screenshot(width=64, height=64, bgra=b"".join(rows))


@pytest.mark.unit
class TestHammingDistance:
    def test_identical(self) -> None:
        assert hamming_distance("abcdef0123456789", "abcdef0123456789") == 0

    def test_one_bit_diff(self) -> None:
        assert hamming_distance("0000000000000001", "0000000000000000") == 1

    def test_mismatched_length_returns_max(self) -> None:
        assert hamming_distance("ff", "ffff") == 64

    def test_empty(self) -> None:
        assert hamming_distance("", "") == 64


@pytest.mark.unit
class TestDetectChange:
    def test_title_change_fires(self) -> None:
        state = ChangeState()
        result = detect_change(_solid_screenshot(), "VS Code", "code.exe", "", state)
        assert result.changed is True
        assert result.reason == "title"
        assert state.title == "VS Code"

    def test_process_change_fires(self) -> None:
        state = ChangeState(title="A", process="proc1", url="", phash="")
        result = detect_change(_solid_screenshot(), "A", "proc2", "", state)
        assert result.changed is True
        assert result.reason == "process"

    def test_url_change_fires(self) -> None:
        state = ChangeState(title="A", process="p", url="http://x", phash="")
        result = detect_change(None, "A", "p", "http://y", state)
        assert result.changed is True
        assert result.reason == "url"

    def test_unchanged_returns_false(self) -> None:
        state = ChangeState()
        first = detect_change(_solid_screenshot(0), "A", "p", "", state)
        assert first.changed is True
        # Same window + same screenshot → no change detected.
        second = detect_change(_solid_screenshot(0), "A", "p", "", state)
        assert second.changed is False
        assert second.reason == "none"

    def test_phash_change_fires(self) -> None:
        state = ChangeState()
        detect_change(_solid_screenshot(0), "A", "p", "", state)
        result = detect_change(_checker_screenshot(), "A", "p", "", state)
        assert result.changed is True
        assert result.reason == "phash"

    def test_no_screenshot_no_phash(self) -> None:
        state = ChangeState(title="A", process="p", url="", phash="abc")
        result = detect_change(None, "A", "p", "", state)
        assert result.changed is False
        assert result.phash == "abc"
