"""Unit tests for the pomodoro timer state machine."""

from __future__ import annotations

import pytest

from tickwise.db.connection import get_connection
from tickwise.pomodoro.timer import (
    PomodoroSettings,
    PomodoroState,
    PomodoroTimer,
)


def _short_settings() -> PomodoroSettings:
    return PomodoroSettings(
        work_minutes=1,
        short_break_minutes=1,
        long_break_minutes=1,
        cycles_before_long=4,
        auto_start=False,
    )


@pytest.mark.unit
class TestStateTransitions:
    def test_starts_idle(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        snap = timer.snapshot()
        assert snap.state == PomodoroState.IDLE
        assert snap.remaining_secs == 0

    def test_start_focus_persists_session(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        snap = timer.start_focus()
        assert snap.state == PomodoroState.FOCUS
        assert snap.remaining_secs == 60
        assert snap.current_session_id is not None
        row = (
            get_connection()
            .execute(
                "SELECT type, completed FROM pomodoro_sessions WHERE id = ?",
                (snap.current_session_id,),
            )
            .fetchone()
        )
        assert row["type"] == "work"
        assert row["completed"] == 0

    def test_stop_marks_session_incomplete(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        snap = timer.start_focus()
        sid = snap.current_session_id
        timer.stop()
        row = (
            get_connection()
            .execute("SELECT completed, ended_at FROM pomodoro_sessions WHERE id = ?", (sid,))
            .fetchone()
        )
        assert row["completed"] == 0
        assert row["ended_at"] is not None

    def test_current_focus_session_only_during_focus(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        assert timer.current_focus_session_id() is None
        timer.start_focus()
        assert timer.current_focus_session_id() is not None
        timer.start_short_break()
        assert timer.current_focus_session_id() is None


@pytest.mark.unit
class TestTickAndComplete:
    def test_tick_decrements_remaining(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        timer.start_focus()
        before = timer.snapshot().remaining_secs
        timer._tick()
        assert timer.snapshot().remaining_secs == before - 1

    def test_complete_marks_completed_and_increments_count(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        timer.start_focus()
        # Force completion: drain the timer
        for _ in range(timer.snapshot().remaining_secs):
            timer._tick()
        snap = timer.snapshot()
        assert snap.completed_focus_count == 1
        assert snap.state == PomodoroState.IDLE  # auto_start=False

    def test_long_break_after_n_cycles(self, tmp_db) -> None:
        cfg = PomodoroSettings(
            work_minutes=1,
            short_break_minutes=1,
            long_break_minutes=1,
            cycles_before_long=2,
            auto_start=True,
        )
        timer = PomodoroTimer(cfg)
        timer.start_focus()
        # Cycle 1: focus → short_break
        for _ in range(60):
            timer._tick()
        assert timer.snapshot().state == PomodoroState.SHORT_BREAK
        # Drain break → next focus
        for _ in range(60):
            timer._tick()
        assert timer.snapshot().state == PomodoroState.FOCUS
        # Cycle 2 finishes → expect long break
        for _ in range(60):
            timer._tick()
        assert timer.snapshot().state == PomodoroState.LONG_BREAK


@pytest.mark.unit
class TestListeners:
    def test_emits_transition_and_tick(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        events: list[tuple[str, str]] = []
        timer.add_listener(lambda evt, snap: events.append((evt, snap.state.value)))
        timer.start_focus()
        timer._tick()
        assert events[0] == ("transition", "focus")
        assert events[1] == ("tick", "focus")

    def test_remove_listener(self, tmp_db) -> None:
        timer = PomodoroTimer(_short_settings())
        events: list[str] = []
        listener = lambda evt, snap: events.append(evt)  # noqa: E731
        timer.add_listener(listener)
        timer.remove_listener(listener)
        timer.start_focus()
        assert events == []
