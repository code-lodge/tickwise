"""Unit tests for tickwise.sessions.tracker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tickwise.capture.window_info import WindowInfo
from tickwise.db.connection import get_connection
from tickwise.sessions.tracker import (
    SessionTracker,
    today_total_seconds,
    total_seconds_since,
)


def _w(title: str, process: str = "proc") -> WindowInfo:
    return WindowInfo(title=title, process_name=process, pid=1)


@pytest.mark.unit
class TestSessionTracker:
    def test_first_extend_opens_session(self, tmp_db: Path) -> None:
        tracker = SessionTracker(min_session_duration=1)
        now = datetime.now(UTC)
        tracker.extend(_w("A"), now)
        assert tracker.open_session is not None
        assert tracker.open_session.title == "A"

    def test_same_window_extends_in_place(self, tmp_db: Path) -> None:
        tracker = SessionTracker(min_session_duration=1)
        t0 = datetime.now(UTC)
        tracker.extend(_w("A"), t0)
        tracker.extend(_w("A"), t0 + timedelta(seconds=10))
        assert tracker.open_session is not None
        assert tracker.open_session.started_at == t0
        assert tracker.open_session.last_seen_at == t0 + timedelta(seconds=10)

    def test_window_change_closes_and_persists(self, tmp_db: Path) -> None:
        tracker = SessionTracker(min_session_duration=1)
        t0 = datetime.now(UTC)
        tracker.extend(_w("A"), t0)
        tracker.extend(_w("A"), t0 + timedelta(seconds=30))
        tracker.extend(_w("B"), t0 + timedelta(seconds=31))

        rows = get_connection().execute("SELECT * FROM sessions").fetchall()
        assert len(rows) == 1
        assert rows[0]["duration_secs"] == 30
        assert rows[0]["llm_classified"] == 0
        assert tracker.open_session is not None
        assert tracker.open_session.title == "B"

    def test_short_session_discarded(self, tmp_db: Path) -> None:
        tracker = SessionTracker(min_session_duration=10)
        t0 = datetime.now(UTC)
        tracker.extend(_w("A"), t0)
        tracker.extend(_w("A"), t0 + timedelta(seconds=3))
        tracker.extend(_w("B"), t0 + timedelta(seconds=4))

        rows = get_connection().execute("SELECT * FROM sessions").fetchall()
        assert rows == []

    def test_gap_above_merge_threshold_splits(self, tmp_db: Path) -> None:
        tracker = SessionTracker(idle_merge_threshold=5, min_session_duration=1)
        t0 = datetime.now(UTC)
        tracker.extend(_w("A"), t0)
        tracker.extend(_w("A"), t0 + timedelta(seconds=2))
        # Gap of 60s on the SAME window — should still split.
        tracker.extend(_w("A"), t0 + timedelta(seconds=62))

        rows = get_connection().execute("SELECT * FROM sessions").fetchall()
        assert len(rows) == 1
        assert rows[0]["duration_secs"] == 2

    def test_flush_persists_open_session(self, tmp_db: Path) -> None:
        tracker = SessionTracker(min_session_duration=1)
        t0 = datetime.now(UTC)
        tracker.extend(_w("A"), t0)
        tracker.extend(_w("A"), t0 + timedelta(seconds=15))
        tracker.flush()
        rows = get_connection().execute("SELECT * FROM sessions").fetchall()
        assert len(rows) == 1
        assert rows[0]["duration_secs"] == 15

    def test_flush_with_no_open_session(self, tmp_db: Path) -> None:
        tracker = SessionTracker()
        assert tracker.flush() is None


@pytest.mark.unit
class TestTotals:
    def test_total_seconds_since(self, tmp_db: Path) -> None:
        tracker = SessionTracker(min_session_duration=1)
        t0 = datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC)
        tracker.extend(_w("A"), t0)
        tracker.extend(_w("A"), t0 + timedelta(seconds=120))
        tracker.flush()

        total = total_seconds_since(t0 - timedelta(hours=1))
        assert total == 120

    def test_today_total_seconds_zero_when_empty(self, tmp_db: Path) -> None:
        assert today_total_seconds() == 0
