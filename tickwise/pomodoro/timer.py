"""Pomodoro state machine and timer thread.

The state machine has four states: IDLE, FOCUS, SHORT_BREAK,
LONG_BREAK. A single background thread ticks once a second, decrementing
the remaining time and firing transitions when it hits zero. Each focus
period is persisted in `pomodoro_sessions` so the dashboard history view
can render long-term streaks.

The timer is process-wide — the capture loop reads
`current_focus_session_id()` to stamp activities with
`pomodoro_session_id`.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

from tickwise.config import DEFAULTS
from tickwise.db.connection import transaction

logger = logging.getLogger(__name__)


class PomodoroState(StrEnum):
    IDLE = "idle"
    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


@dataclass(slots=True)
class PomodoroSettings:
    work_minutes: int
    short_break_minutes: int
    long_break_minutes: int
    cycles_before_long: int
    auto_start: bool

    @classmethod
    def from_defaults(cls) -> PomodoroSettings:
        return cls(
            work_minutes=int(cast(int, DEFAULTS["pomodoro_work_minutes"])),
            short_break_minutes=int(cast(int, DEFAULTS["pomodoro_short_break_minutes"])),
            long_break_minutes=int(cast(int, DEFAULTS["pomodoro_long_break_minutes"])),
            cycles_before_long=int(cast(int, DEFAULTS["pomodoro_cycles_before_long"])),
            auto_start=bool(DEFAULTS["pomodoro_auto_start"]),
        )


@dataclass(slots=True)
class PomodoroSnapshot:
    state: PomodoroState
    remaining_secs: int
    duration_secs: int
    completed_focus_count: int
    current_session_id: int | None
    started_at: str | None


# Listener signature: (event_type, snapshot) → None. Used by the WebSocket
# bridge so dashboards can react to ticks and transitions.
Listener = Callable[[str, PomodoroSnapshot], None]


class PomodoroTimer:
    """State machine + ticking thread. Thread-safe; one instance per process."""

    def __init__(self, settings: PomodoroSettings | None = None) -> None:
        self._settings = settings or PomodoroSettings.from_defaults()
        self._lock = threading.RLock()
        self._state = PomodoroState.IDLE
        self._remaining = 0
        self._duration = 0
        self._completed_focus = 0
        self._current_id: int | None = None
        self._started_at: datetime | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._listeners: list[Listener] = []

    # ─── Public API ──────────────────────────────────────────────────

    @property
    def settings(self) -> PomodoroSettings:
        return self._settings

    def update_settings(self, settings: PomodoroSettings) -> None:
        with self._lock:
            self._settings = settings

    def add_listener(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def snapshot(self) -> PomodoroSnapshot:
        with self._lock:
            return PomodoroSnapshot(
                state=self._state,
                remaining_secs=self._remaining,
                duration_secs=self._duration,
                completed_focus_count=self._completed_focus,
                current_session_id=self._current_id,
                started_at=self._started_at.isoformat() if self._started_at else None,
            )

    def current_focus_session_id(self) -> int | None:
        """Return the active focus session id, or None when not in FOCUS."""
        with self._lock:
            return self._current_id if self._state == PomodoroState.FOCUS else None

    def start_focus(self) -> PomodoroSnapshot:
        return self._enter(PomodoroState.FOCUS)

    def start_short_break(self) -> PomodoroSnapshot:
        return self._enter(PomodoroState.SHORT_BREAK)

    def start_long_break(self) -> PomodoroSnapshot:
        return self._enter(PomodoroState.LONG_BREAK)

    def stop(self) -> PomodoroSnapshot:
        """End the current period (manual abort, marks session incomplete)."""
        with self._lock:
            if self._state != PomodoroState.IDLE and self._current_id is not None:
                self._close_session(self._current_id, completed=False)
            self._state = PomodoroState.IDLE
            self._remaining = 0
            self._duration = 0
            self._current_id = None
            self._started_at = None
            snap = self.snapshot()
        self._emit("transition", snap)
        return snap

    def start_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="PomodoroTimer", daemon=True)
        self._thread.start()

    def stop_thread(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ─── Internals ───────────────────────────────────────────────────

    def _run(self) -> None:
        logger.info("Pomodoro timer thread started")
        while not self._stop.wait(1.0):
            self._tick()
        logger.info("Pomodoro timer thread stopped")

    def _tick(self) -> None:
        transition: tuple[PomodoroState, PomodoroState] | None = None
        with self._lock:
            if self._state == PomodoroState.IDLE or self._remaining <= 0:
                return
            self._remaining -= 1
            if self._remaining <= 0:
                # Period complete — record + decide what's next.
                if self._current_id is not None:
                    self._close_session(self._current_id, completed=True)
                if self._state == PomodoroState.FOCUS:
                    self._completed_focus += 1
                    next_state = (
                        PomodoroState.LONG_BREAK
                        if self._completed_focus % self._settings.cycles_before_long == 0
                        else PomodoroState.SHORT_BREAK
                    )
                else:
                    next_state = PomodoroState.FOCUS
                transition = (self._state, next_state)
                if self._settings.auto_start:
                    self._enter_locked(next_state)
                else:
                    self._state = PomodoroState.IDLE
                    self._duration = 0
                    self._current_id = None
                    self._started_at = None
        snap = self.snapshot()
        if transition is not None:
            self._emit("complete", snap)
        else:
            self._emit("tick", snap)

    def _enter(self, state: PomodoroState) -> PomodoroSnapshot:
        with self._lock:
            if self._state != PomodoroState.IDLE and self._current_id is not None:
                self._close_session(self._current_id, completed=False)
            self._enter_locked(state)
            snap = self.snapshot()
        self._emit("transition", snap)
        return snap

    def _enter_locked(self, state: PomodoroState) -> None:
        duration_min = {
            PomodoroState.FOCUS: self._settings.work_minutes,
            PomodoroState.SHORT_BREAK: self._settings.short_break_minutes,
            PomodoroState.LONG_BREAK: self._settings.long_break_minutes,
        }[state]
        self._state = state
        self._duration = max(1, duration_min) * 60
        self._remaining = self._duration
        self._started_at = datetime.now(tz=UTC)
        self._current_id = self._open_session(state)

    def _open_session(self, state: PomodoroState) -> int:
        type_map = {
            PomodoroState.FOCUS: "work",
            PomodoroState.SHORT_BREAK: "short_break",
            PomodoroState.LONG_BREAK: "long_break",
        }
        with transaction() as conn:
            cur = conn.execute(
                "INSERT INTO pomodoro_sessions (type, started_at) VALUES (?, ?)",
                (type_map[state], self._started_at.isoformat() if self._started_at else None),
            )
            return int(cur.lastrowid or 0)

    def _close_session(self, session_id: int, *, completed: bool) -> None:
        with transaction() as conn:
            conn.execute(
                "UPDATE pomodoro_sessions SET ended_at = ?, completed = ? WHERE id = ?",
                (datetime.now(tz=UTC).isoformat(), 1 if completed else 0, session_id),
            )

    def _emit(self, event: str, snapshot: PomodoroSnapshot) -> None:
        for listener in list(self._listeners):
            try:
                listener(event, snapshot)
            except Exception:  # noqa: BLE001
                logger.exception("Pomodoro listener raised")


def snapshot_to_dict(snap: PomodoroSnapshot) -> dict[str, Any]:
    return {
        "state": snap.state.value,
        "remaining_secs": snap.remaining_secs,
        "duration_secs": snap.duration_secs,
        "completed_focus_count": snap.completed_focus_count,
        "current_session_id": snap.current_session_id,
        "started_at": snap.started_at,
    }
