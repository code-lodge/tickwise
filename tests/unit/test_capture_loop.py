"""Unit tests for tickwise.capture.loop."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from tickwise.capture.loop import CaptureLoop
from tickwise.capture.screenshot import Screenshot
from tickwise.capture.window_info import WindowInfo
from tickwise.classification import queue as cq
from tickwise.db.connection import get_connection


def _solid_screenshot() -> Screenshot:
    return Screenshot(width=64, height=64, bgra=bytes([0, 0, 0, 255]) * 64 * 64)


def _other_screenshot() -> Screenshot:
    return Screenshot(width=64, height=64, bgra=bytes([255, 255, 255, 255]) * 64 * 64)


@pytest.fixture(autouse=True)
def _drain_queue() -> Any:
    cq.clear()
    yield
    cq.clear()


@pytest.mark.unit
class TestCaptureLoopTick:
    def test_change_persists_activity_and_enqueues(self, tmp_db: Path) -> None:
        extends: list[tuple[WindowInfo, datetime]] = []
        changes: list[tuple[WindowInfo, datetime]] = []

        loop = CaptureLoop(
            ocr_runner=lambda _shot, _w: "hello world",
            on_session_extend=lambda w, n: extends.append((w, n)),
            on_session_change=lambda w, n: changes.append((w, n)),
        )

        with (
            patch("tickwise.capture.loop.get_idle_seconds", return_value=0.0),
            patch(
                "tickwise.capture.loop.get_active_window",
                return_value=WindowInfo(title="VS Code", process_name="code.exe", pid=1),
            ),
            patch.object(loop, "_safe_capture", return_value=_solid_screenshot()),
            patch.object(loop, "_safe_capture_all", return_value={1: _solid_screenshot()}),
        ):
            changed = loop.tick_once()

        assert changed is True
        assert changes and not extends
        rows = get_connection().execute("SELECT * FROM activities").fetchall()
        assert len(rows) == 1
        assert rows[0]["window_title"] == "VS Code"
        assert rows[0]["process_name"] == "code.exe"
        assert rows[0]["source"] == "unclassified"
        assert rows[0]["change_detected"] == 1
        assert rows[0]["ocr_text"] == "hello world"

        # Job pushed to queue.
        job = cq.take(timeout=0.5)
        assert job is not None
        assert job.window_title == "VS Code"

    def test_no_change_extends_session(self, tmp_db: Path) -> None:
        extends: list[tuple[WindowInfo, datetime]] = []

        loop = CaptureLoop(
            ocr_runner=lambda _s, _w: "",
            on_session_extend=lambda w, n: extends.append((w, n)),
        )

        win = WindowInfo(title="A", process_name="p", pid=1)
        with (
            patch("tickwise.capture.loop.get_idle_seconds", return_value=0.0),
            patch("tickwise.capture.loop.get_active_window", return_value=win),
            patch.object(loop, "_safe_capture", return_value=_solid_screenshot()),
            patch.object(loop, "_safe_capture_all", return_value={1: _solid_screenshot()}),
        ):
            assert loop.tick_once() is True  # first sample = change
            assert loop.tick_once() is False  # same screenshot = no change

        assert len(extends) == 1
        rows = get_connection().execute("SELECT * FROM activities").fetchall()
        assert len(rows) == 1

    def test_idle_above_threshold_skips(self, tmp_db: Path) -> None:
        loop = CaptureLoop(idle_split_threshold=10, ocr_runner=lambda _s, _w: "")
        with patch("tickwise.capture.loop.get_idle_seconds", return_value=999.0):
            assert loop.tick_once() is False
        assert loop.last_idle_seconds == 999.0
        assert get_connection().execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0

    def test_pause_resume_flags(self, tmp_db: Path) -> None:
        loop = CaptureLoop()
        assert loop.is_paused is False
        loop.pause()
        assert loop.is_paused is True
        loop.resume()
        assert loop.is_paused is False

    def test_screenshot_failure_falls_through(self, tmp_db: Path) -> None:
        loop = CaptureLoop(ocr_runner=lambda _s, _w: "")
        with (
            patch("tickwise.capture.loop.get_idle_seconds", return_value=0.0),
            patch(
                "tickwise.capture.loop.get_active_window",
                return_value=WindowInfo(title="X", process_name="x", pid=1),
            ),
            patch.object(loop, "_safe_capture", return_value=None),
            patch.object(loop, "_safe_capture_all", return_value={1: _solid_screenshot()}),
        ):
            # Title change still fires even without a screenshot.
            assert loop.tick_once() is True

    def test_change_after_window_switch(self, tmp_db: Path) -> None:
        loop = CaptureLoop(ocr_runner=lambda _s, _w: "")
        with (
            patch("tickwise.capture.loop.get_idle_seconds", return_value=0.0),
            patch.object(loop, "_safe_capture", return_value=_solid_screenshot()),
            patch.object(loop, "_safe_capture_all", return_value={1: _solid_screenshot()}),
        ):
            with patch(
                "tickwise.capture.loop.get_active_window",
                return_value=WindowInfo(title="A", process_name="p", pid=1),
            ):
                loop.tick_once()
            with patch(
                "tickwise.capture.loop.get_active_window",
                return_value=WindowInfo(title="B", process_name="p", pid=1),
            ):
                changed = loop.tick_once()
        assert changed is True
        rows = get_connection().execute("SELECT window_title FROM activities ORDER BY id").fetchall()
        assert [r["window_title"] for r in rows] == ["A", "B"]


@pytest.mark.unit
class TestCaptureLoopThreadLifecycle:
    def test_start_stop_no_capturer(self) -> None:
        loop = CaptureLoop(tick_seconds=0.05)
        # Force the thread to bail immediately by having ScreenCapturer raise.
        with patch(
            "tickwise.capture.loop.ScreenCapturer",
            side_effect=RuntimeError("mss missing"),
        ):
            loop.start()
            loop.stop(join_timeout=1.0)
        assert loop.is_running is False
