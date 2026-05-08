"""Unit tests for chronolens.capture.idle_detector_macos."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chronolens.capture import idle_detector_macos as mod


@pytest.mark.unit
class TestIdleDetectorMacOS:
    def test_returns_zero_when_no_backend_available(self) -> None:
        with (
            patch.object(mod, "_idle_via_quartz", return_value=None),
            patch.object(mod, "_idle_via_ioreg", return_value=None),
        ):
            assert mod.get_idle_seconds() == 0.0

    def test_prefers_quartz_over_ioreg(self) -> None:
        with (
            patch.object(mod, "_idle_via_quartz", return_value=12.5),
            patch.object(mod, "_idle_via_ioreg") as ioreg,
        ):
            assert mod.get_idle_seconds() == 12.5
            ioreg.assert_not_called()

    def test_falls_back_to_ioreg(self) -> None:
        with (
            patch.object(mod, "_idle_via_quartz", return_value=None),
            patch.object(mod, "_idle_via_ioreg", return_value=3.0),
        ):
            assert mod.get_idle_seconds() == 3.0

    def test_skips_negative_values(self) -> None:
        with (
            patch.object(mod, "_idle_via_quartz", return_value=-1.0),
            patch.object(mod, "_idle_via_ioreg", return_value=2.0),
        ):
            assert mod.get_idle_seconds() == 2.0

    def test_ioreg_parses_hidIdleTime(self) -> None:
        sample = '          | |   "HIDIdleTime" = 1234567890\n'
        completed = MagicMock(returncode=0, stdout=sample)
        with patch.object(mod.subprocess, "run", return_value=completed):
            assert mod._idle_via_ioreg() == pytest.approx(1.23456789)

    def test_ioreg_returns_none_on_failure(self) -> None:
        with patch.object(mod.subprocess, "run", side_effect=OSError):
            assert mod._idle_via_ioreg() is None
