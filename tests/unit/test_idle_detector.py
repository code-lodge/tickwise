"""Unit tests for tickwise.capture.idle_detector dispatcher."""

from __future__ import annotations

import sys

import pytest

from tickwise.capture.idle_detector import get_idle_seconds


@pytest.mark.unit
class TestIdleDetector:
    def test_returns_non_negative_float(self) -> None:
        v = get_idle_seconds()
        assert isinstance(v, float)
        assert v >= 0.0

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
    def test_windows_backend_returns_float(self) -> None:
        from tickwise.capture.idle_detector_windows import get_idle_seconds as gw

        v = gw()
        assert isinstance(v, float)
        assert v >= 0.0
