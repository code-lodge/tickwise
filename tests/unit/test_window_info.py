"""Unit tests for tickwise.capture.window_info dispatcher."""

from __future__ import annotations

import sys

import pytest

from tickwise.capture.window_info import WindowInfo, get_active_window


@pytest.mark.unit
class TestWindowInfoDispatcher:
    def test_returns_windowinfo_instance(self) -> None:
        info = get_active_window()
        assert isinstance(info, WindowInfo)
        assert isinstance(info.title, str)
        assert isinstance(info.process_name, str)

    def test_dataclass_is_frozen(self) -> None:
        info = WindowInfo(title="t", process_name="p", pid=1)
        with pytest.raises(AttributeError):
            info.title = "other"  # type: ignore[misc]

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
    def test_windows_backend_imports(self) -> None:
        from tickwise.capture.window_info_windows import get_active_window as gw

        info = gw()
        assert isinstance(info, WindowInfo)
