"""Session aggregation: turn individual ticks into time blocks.

The tracker keeps an "open session" in memory keyed by (process, title).
Each tick that lands on the same window extends the open session;
a window change closes the previous session and opens a new one. Sessions
shorter than `min_session_duration` are discarded; gaps shorter than
`idle_merge_threshold` are merged into the previous session.

Phase 1 only persists raw, unclassified sessions — `project_id`,
`category_id`, `description`, and `confidence` stay NULL until the LLM
pipeline lands in Phase 3.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import cast

from chronolens.capture.window_info import WindowInfo
from chronolens.config import DEFAULTS
from chronolens.db.connection import transaction

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _OpenSession:
    process: str
    title: str
    started_at: datetime
    last_seen_at: datetime
    description: str | None = None
    activity_ids: list[int] = field(default_factory=list)


class SessionTracker:
    """Thread-safe accumulator that flushes completed sessions to SQLite."""

    def __init__(
        self,
        *,
        idle_merge_threshold: float | None = None,
        min_session_duration: float | None = None,
    ) -> None:
        self._merge_threshold = float(
            idle_merge_threshold if idle_merge_threshold is not None else cast(int, DEFAULTS["idle_merge_threshold"])
        )
        self._min_duration = float(
            min_session_duration if min_session_duration is not None else cast(int, DEFAULTS["min_session_duration"])
        )
        self._lock = threading.Lock()
        self._open: _OpenSession | None = None

    @property
    def open_session(self) -> _OpenSession | None:
        """Currently open session, if any (snapshot — caller should not mutate)."""
        return self._open

    def extend(self, window: WindowInfo, now: datetime) -> None:
        """Record that `window` is still focused at time `now`.

        If no session is open, start one. If the open session is for a
        different window, close it and open a fresh one. If the gap since
        the last sample exceeds `idle_merge_threshold`, also close and
        reopen — we treat that as a discontinuity.
        """
        with self._lock:
            if self._open is None:
                self._open = _OpenSession(
                    process=window.process_name,
                    title=window.title,
                    started_at=now,
                    last_seen_at=now,
                )
                return

            same_window = self._open.process == window.process_name and self._open.title == window.title
            gap = (now - self._open.last_seen_at).total_seconds()
            if same_window and gap <= self._merge_threshold:
                self._open.last_seen_at = now
                return

            self._close_locked(closed_at=self._open.last_seen_at)
            self._open = _OpenSession(
                process=window.process_name,
                title=window.title,
                started_at=now,
                last_seen_at=now,
            )

    def on_change(self, window: WindowInfo, now: datetime) -> None:
        """Called when the capture loop detects a screen change.

        Logically equivalent to `extend()` for Phase 1 — we use the same
        merge rules. Future phases can attach the activity_id here.
        """
        self.extend(window, now)

    def flush(self) -> int | None:
        """Close and persist the open session (if any). Returns its row id."""
        with self._lock:
            if self._open is None:
                return None
            ended = self._open.last_seen_at
            return self._close_locked(closed_at=ended)

    # ─── internals ────────────────────────────────────────────────────────

    def _close_locked(self, closed_at: datetime) -> int | None:
        assert self._open is not None  # noqa: S101 — invariant under self._lock
        sess = self._open
        self._open = None
        duration = (closed_at - sess.started_at).total_seconds()
        if duration < self._min_duration:
            logger.debug(
                "discarding short session %s/%s duration=%.1fs",
                sess.process,
                sess.title,
                duration,
            )
            return None
        try:
            with transaction() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO sessions
                        (started_at, ended_at, duration_secs, description,
                         is_manual, llm_classified)
                    VALUES (?, ?, ?, ?, 0, 0)
                    """,
                    (
                        sess.started_at.isoformat(),
                        closed_at.isoformat(),
                        int(duration),
                        f"{sess.process} — {sess.title}".strip(" —") or None,
                    ),
                )
                row_id = cur.lastrowid
            return int(row_id) if row_id is not None else None
        except Exception:
            logger.exception("failed to persist session")
            return None


# ─── module-level helpers for read queries ────────────────────────────────


def total_seconds_since(start: datetime) -> int:
    """Sum of `duration_secs` across all sessions started at or after `start`.

    Used by the tray icon to display "today's total" without opening a
    transaction context manager every second.
    """
    from chronolens.db.connection import get_connection

    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(duration_secs), 0) FROM sessions WHERE started_at >= ?",
        (start.isoformat(),),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def today_total_seconds(now: datetime | None = None) -> int:
    """Total tracked seconds for today (UTC midnight to now)."""
    moment = now or datetime.now(tz=None).astimezone()
    midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if moment.tzinfo is None:
        midnight = midnight - timedelta(seconds=0)
    return total_seconds_since(midnight)
