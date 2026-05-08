"""Integration tests for the CaptureLoop's threaded `_run` path."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tickwise.capture.loop import CaptureLoop
from tickwise.capture.screenshot import Screenshot
from tickwise.capture.window_info import WindowInfo
from tickwise.classification import queue as cq
from tickwise.db.connection import get_connection


def _solid_screenshot() -> Screenshot:
    return Screenshot(width=64, height=64, bgra=bytes([0, 0, 0, 255]) * 64 * 64)


@pytest.fixture(autouse=True)
def _drain_queue() -> None:
    cq.clear()
    yield
    cq.clear()


@pytest.mark.integration
class TestCaptureLoopThread:
    def test_run_persists_activities_and_stops_cleanly(self, tmp_db: Path) -> None:
        """Drive the real `_run` thread: it should tick, persist, then stop on signal."""
        ticks_completed = threading.Event()

        original_tick_once = CaptureLoop.tick_once
        call_count = {"n": 0}

        def counting_tick(self: CaptureLoop) -> bool:
            result = original_tick_once(self)
            call_count["n"] += 1
            if call_count["n"] >= 2:
                ticks_completed.set()
            return result

        loop = CaptureLoop(tick_seconds=0.05, ocr_runner=lambda _s, _w: "")

        fake_capturer = MagicMock()
        fake_capturer.capture_primary.return_value = _solid_screenshot()
        fake_capturer.list_monitors.return_value = []
        fake_capturer.capture_all.return_value = {1: _solid_screenshot()}

        windows = [
            WindowInfo(title="A", process_name="p", pid=1),
            WindowInfo(title="B", process_name="p", pid=1),
        ]

        def next_window() -> WindowInfo:
            return windows[min(call_count["n"], len(windows) - 1)]

        with (
            patch("tickwise.capture.loop.ScreenCapturer", return_value=fake_capturer),
            patch("tickwise.capture.loop.get_idle_seconds", return_value=0.0),
            patch("tickwise.capture.loop.get_active_window", side_effect=next_window),
            patch.object(CaptureLoop, "tick_once", counting_tick),
        ):
            loop.start()
            assert ticks_completed.wait(timeout=5.0), "loop did not tick twice in 5s"
            loop.stop(join_timeout=2.0)

        assert loop.is_running is False
        # Each window change persisted exactly one row.
        rows = get_connection().execute("SELECT window_title FROM activities ORDER BY id").fetchall()
        assert [r["window_title"] for r in rows] == ["A", "B"]

    def test_pause_skips_ticks_until_resume(self, tmp_db: Path) -> None:
        """A paused loop must not call tick_once until it's resumed."""
        ticks_after_resume = threading.Event()
        call_count = {"n": 0}

        original = CaptureLoop.tick_once

        def counting(self: CaptureLoop) -> bool:
            call_count["n"] += 1
            ticks_after_resume.set()
            return original(self)

        loop = CaptureLoop(tick_seconds=0.02, ocr_runner=lambda _s, _w: "")
        fake_capturer = MagicMock()
        fake_capturer.capture_primary.return_value = _solid_screenshot()
        fake_capturer.list_monitors.return_value = []
        fake_capturer.capture_all.return_value = {1: _solid_screenshot()}

        with (
            patch("tickwise.capture.loop.ScreenCapturer", return_value=fake_capturer),
            patch("tickwise.capture.loop.get_idle_seconds", return_value=0.0),
            patch(
                "tickwise.capture.loop.get_active_window",
                return_value=WindowInfo(title="A", process_name="p", pid=1),
            ),
            patch.object(CaptureLoop, "tick_once", counting),
        ):
            loop.pause()
            loop.start()
            # Give the thread a moment to spin while paused.
            assert not ticks_after_resume.wait(timeout=0.2), "tick fired while paused"
            assert call_count["n"] == 0
            loop.resume()
            assert ticks_after_resume.wait(timeout=2.0), "tick did not fire after resume"
            loop.stop(join_timeout=2.0)

    def test_stop_is_idempotent(self, tmp_db: Path) -> None:
        loop = CaptureLoop(tick_seconds=0.05)
        with patch("tickwise.capture.loop.ScreenCapturer", side_effect=RuntimeError("no mss")):
            loop.start()
            loop.stop(join_timeout=1.0)
            loop.stop(join_timeout=1.0)  # second stop should be a no-op
        assert loop.is_running is False
