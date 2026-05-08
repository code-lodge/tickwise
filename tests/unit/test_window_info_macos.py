"""Unit tests for tickwise.capture.window_info_macos.

These tests don't import AppKit — they exercise the module's logic by
patching the lazy importers, so they pass on any host OS.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tickwise.capture import window_info_macos as mod
from tickwise.capture.window_info import WindowInfo


@pytest.mark.unit
class TestWindowInfoMacOS:
    def test_returns_empty_when_appkit_missing(self) -> None:
        with patch.object(mod, "_frontmost_app", return_value=None):
            info = mod.get_active_window()
        assert info == WindowInfo(title="", process_name="", pid=None)

    def test_falls_back_to_empty_title_when_accessibility_denied(self) -> None:
        fake_app = MagicMock()
        fake_app.localizedName.return_value = "Code"
        fake_app.processIdentifier.return_value = 1234
        with (
            patch.object(mod, "_frontmost_app", return_value=fake_app),
            patch.object(mod, "_accessibility_window_title", return_value=""),
        ):
            info = mod.get_active_window()
        assert info.process_name == "Code"
        assert info.pid == 1234
        assert info.title == ""

    def test_returns_full_info_with_accessibility(self) -> None:
        fake_app = MagicMock()
        fake_app.localizedName.return_value = "Slack"
        fake_app.processIdentifier.return_value = 555
        with (
            patch.object(mod, "_frontmost_app", return_value=fake_app),
            patch.object(mod, "_accessibility_window_title", return_value="#general"),
        ):
            info = mod.get_active_window()
        assert info == WindowInfo(title="#general", process_name="Slack", pid=555)
