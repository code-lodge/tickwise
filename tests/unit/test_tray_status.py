"""Unit tests for the tray status text helpers (no pystray needed)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tickwise import runtime
from tickwise.capture.window_info import WindowInfo
from tickwise.tray import (
    _COLOR_IDLE,
    _COLOR_NEUTRAL,
    _COLOR_PAUSED,
    _COLOR_TRACKING,
    _format_duration,
    _icon_color,
    build_status_text,
    build_today_total_text,
)


@pytest.fixture(autouse=True)
def _reset_runtime() -> None:
    runtime.set_capture_loop(None)
    runtime.set_session_tracker(None)


@pytest.mark.unit
class TestFormatDuration:
    def test_seconds(self) -> None:
        assert _format_duration(45) == "45s"

    def test_minutes(self) -> None:
        assert _format_duration(180) == "3m"

    def test_hours(self) -> None:
        assert _format_duration(3 * 3600 + 42 * 60) == "3h 42m"


@pytest.mark.unit
class TestStatusText:
    def test_no_loop(self) -> None:
        assert build_status_text() == "Tickwise — Not tracking"

    def test_paused(self) -> None:
        loop = MagicMock()
        loop.is_running = True
        loop.is_paused = True
        runtime.set_capture_loop(loop)
        assert build_status_text() == "Tickwise — Paused"

    def test_active_with_session(self) -> None:
        loop = MagicMock()
        loop.is_running = True
        loop.is_paused = False
        loop.last_window = WindowInfo(title="x", process_name="code.exe", pid=1)
        runtime.set_capture_loop(loop)

        tracker = MagicMock()
        open_session = MagicMock()
        open_session.started_at = datetime.now(UTC)
        tracker.open_session = open_session
        runtime.set_session_tracker(tracker)

        assert build_status_text().startswith("Tickwise — code.exe")


@pytest.mark.unit
class TestTodayTotalText:
    def test_returns_zero_when_empty(self, tmp_db: Path) -> None:
        assert build_today_total_text() == "0s today"


@pytest.mark.unit
class TestIconColor:
    def test_neutral_when_no_loop(self) -> None:
        assert _icon_color() == _COLOR_NEUTRAL

    def test_neutral_when_not_running(self) -> None:
        loop = MagicMock()
        loop.is_running = False
        runtime.set_capture_loop(loop)
        assert _icon_color() == _COLOR_NEUTRAL

    def test_paused(self) -> None:
        loop = MagicMock()
        loop.is_running = True
        loop.is_paused = True
        runtime.set_capture_loop(loop)
        assert _icon_color() == _COLOR_PAUSED

    def test_tracking(self) -> None:
        loop = MagicMock()
        loop.is_running = True
        loop.is_paused = False
        loop.last_idle_seconds = 0.0
        runtime.set_capture_loop(loop)
        assert _icon_color() == _COLOR_TRACKING

    def test_idle(self) -> None:
        loop = MagicMock()
        loop.is_running = True
        loop.is_paused = False
        loop.last_idle_seconds = 600.0
        runtime.set_capture_loop(loop)
        assert _icon_color() == _COLOR_IDLE
