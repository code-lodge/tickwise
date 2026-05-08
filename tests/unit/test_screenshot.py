"""Unit tests for tickwise.capture.screenshot."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from tickwise.capture.screenshot import ScreenCapturer, Screenshot


@pytest.mark.unit
class TestScreenshotDataclass:
    def test_construction(self) -> None:
        shot = Screenshot(width=10, height=20, bgra=b"\x00" * 800)
        assert shot.width == 10
        assert shot.height == 20
        assert len(shot.bgra) == 800

    def test_immutable(self) -> None:
        shot = Screenshot(width=1, height=1, bgra=b"\x00\x00\x00\x00")
        with pytest.raises(AttributeError):
            shot.width = 99  # type: ignore[misc]


@pytest.mark.unit
class TestScreenCapturer:
    def test_capture_primary_uses_monitor_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_mss = MagicMock()
        fake_grab = MagicMock()
        fake_grab.width = 100
        fake_grab.height = 50
        fake_grab.bgra = b"\x00" * (100 * 50 * 4)

        instance = MagicMock()
        instance.monitors = [{"top": 0}, {"top": 0, "left": 0, "width": 100, "height": 50}]
        instance.grab.return_value = fake_grab
        fake_mss.mss = MagicMock(return_value=instance)

        import tickwise.capture.screenshot as mod

        monkeypatch.setattr(mod, "mss", fake_mss)
        monkeypatch.setattr(mod, "_MSS_AVAILABLE", True)

        cap = ScreenCapturer()
        shot = cap.capture_primary()
        assert shot.width == 100
        assert shot.height == 50
        instance.grab.assert_called_once_with(instance.monitors[1])

    def test_no_mss_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import tickwise.capture.screenshot as mod

        monkeypatch.setattr(mod, "_MSS_AVAILABLE", False)
        with pytest.raises(RuntimeError):
            ScreenCapturer()

    def test_context_manager_closes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import tickwise.capture.screenshot as mod

        instance: Any = MagicMock()
        instance.monitors = [{}, {"top": 0, "left": 0, "width": 1, "height": 1}]
        fake_mss = MagicMock()
        fake_mss.mss = MagicMock(return_value=instance)
        monkeypatch.setattr(mod, "mss", fake_mss)
        monkeypatch.setattr(mod, "_MSS_AVAILABLE", True)

        with ScreenCapturer() as _cap:
            pass
        instance.close.assert_called_once()
