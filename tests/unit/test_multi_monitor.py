"""Unit tests for multi-monitor capture + focus routing."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tickwise.capture.loop import _enabled_monitor_indices
from tickwise.capture.screenshot import MonitorInfo


@pytest.mark.unit
class TestMonitorInfo:
    def test_contains_inside(self) -> None:
        m = MonitorInfo(index=1, left=0, top=0, width=1920, height=1080)
        assert m.contains(100, 100)
        assert m.contains(0, 0)
        assert m.contains(1919, 1079)

    def test_contains_outside(self) -> None:
        m = MonitorInfo(index=1, left=0, top=0, width=1920, height=1080)
        assert not m.contains(1920, 100)
        assert not m.contains(-1, 100)
        assert not m.contains(500, 1080)

    def test_offset_monitor(self) -> None:
        m = MonitorInfo(index=2, left=1920, top=0, width=2560, height=1440)
        assert m.contains(2000, 100)
        assert not m.contains(100, 100)


@pytest.mark.unit
class TestEnabledMonitorIndices:
    def test_no_prefs_returns_all(self, tmp_db) -> None:
        detected = [
            MonitorInfo(index=1, left=0, top=0, width=1920, height=1080),
            MonitorInfo(index=2, left=1920, top=0, width=2560, height=1440),
        ]
        assert _enabled_monitor_indices(detected) == [1, 2]

    def test_disabled_monitor_filtered(self, tmp_db) -> None:
        from tickwise.db.connection import transaction

        with transaction() as conn:
            conn.execute("INSERT INTO monitor_preferences (monitor_index, enabled) VALUES (?, 0)", (2,))
            conn.execute("INSERT INTO monitor_preferences (monitor_index, enabled) VALUES (?, 1)", (1,))
        detected = [
            MonitorInfo(index=1, left=0, top=0, width=1920, height=1080),
            MonitorInfo(index=2, left=1920, top=0, width=2560, height=1440),
        ]
        assert _enabled_monitor_indices(detected) == [1]

    def test_unknown_monitor_defaults_enabled(self, tmp_db) -> None:
        from tickwise.db.connection import transaction

        with transaction() as conn:
            conn.execute("INSERT INTO monitor_preferences (monitor_index, enabled) VALUES (?, 1)", (1,))
        detected = [
            MonitorInfo(index=1, left=0, top=0, width=1920, height=1080),
            MonitorInfo(index=2, left=1920, top=0, width=2560, height=1440),
        ]
        assert _enabled_monitor_indices(detected) == [1, 2]


@pytest.mark.unit
class TestPickFocusedMonitor:
    def test_single_monitor_returns_only_index(self) -> None:
        from tickwise.capture.loop import CaptureLoop
        from tickwise.capture.screenshot import Screenshot

        loop = CaptureLoop()
        loop._capturer = None
        shots = {1: Screenshot(width=1920, height=1080, bgra=b"", monitor_index=1)}
        assert loop._pick_focused_monitor(shots) == 1

    def test_window_center_on_secondary(self) -> None:
        from tickwise.capture.loop import CaptureLoop
        from tickwise.capture.screenshot import Screenshot

        loop = CaptureLoop()

        # Stub a capturer that lists two monitors
        class _Cap:
            def list_monitors(self):
                return [
                    MonitorInfo(index=1, left=0, top=0, width=1920, height=1080),
                    MonitorInfo(index=2, left=1920, top=0, width=2560, height=1440),
                ]

        loop._capturer = _Cap()  # type: ignore[assignment]
        shots = {
            1: Screenshot(width=1920, height=1080, bgra=b"", monitor_index=1),
            2: Screenshot(width=2560, height=1440, bgra=b"", monitor_index=2),
        }
        with patch("tickwise.capture.loop.get_window_center", return_value=(2500, 200)):
            assert loop._pick_focused_monitor(shots) == 2

    def test_unknown_window_center_falls_back_to_last_focused(self) -> None:
        from tickwise.capture.loop import CaptureLoop
        from tickwise.capture.screenshot import Screenshot

        loop = CaptureLoop()
        loop._last_focused_index = 2

        class _Cap:
            def list_monitors(self):
                return [
                    MonitorInfo(index=1, left=0, top=0, width=1920, height=1080),
                    MonitorInfo(index=2, left=1920, top=0, width=2560, height=1440),
                ]

        loop._capturer = _Cap()  # type: ignore[assignment]
        shots = {
            1: Screenshot(width=1920, height=1080, bgra=b"", monitor_index=1),
            2: Screenshot(width=2560, height=1440, bgra=b"", monitor_index=2),
        }
        with patch("tickwise.capture.loop.get_window_center", return_value=None):
            assert loop._pick_focused_monitor(shots) == 2
