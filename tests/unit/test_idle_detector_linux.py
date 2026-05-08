"""Unit tests for chronolens.capture.idle_detector_linux."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chronolens.capture import idle_detector_linux as mod


@pytest.mark.unit
class TestIdleDetectorLinux:
    def test_returns_zero_when_all_backends_fail(self) -> None:
        with (
            patch.object(mod, "_idle_via_xprintidle", return_value=None),
            patch.object(mod, "_idle_via_dbus", return_value=None),
            patch.object(mod, "_idle_via_xlib", return_value=None),
        ):
            assert mod.get_idle_seconds() == 0.0

    def test_prefers_xprintidle(self) -> None:
        with (
            patch.object(mod, "_idle_via_xprintidle", return_value=4.2),
            patch.object(mod, "_idle_via_dbus") as dbus,
        ):
            assert mod.get_idle_seconds() == 4.2
            dbus.assert_not_called()

    def test_xprintidle_parses_ms(self) -> None:
        completed = MagicMock(returncode=0, stdout="6500\n")
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/xprintidle"),
            patch.object(mod.subprocess, "run", return_value=completed),
        ):
            assert mod._idle_via_xprintidle() == pytest.approx(6.5)

    def test_xprintidle_skipped_without_binary(self) -> None:
        with patch.object(mod.shutil, "which", return_value=None):
            assert mod._idle_via_xprintidle() is None

    def test_dbus_parses_uint32(self) -> None:
        completed = MagicMock(returncode=0, stdout="   uint32 12000\n")
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/dbus-send"),
            patch.object(mod.subprocess, "run", return_value=completed),
        ):
            assert mod._idle_via_dbus() == pytest.approx(12.0)

    def test_dbus_skipped_without_binary(self) -> None:
        with patch.object(mod.shutil, "which", return_value=None):
            assert mod._idle_via_dbus() is None
