"""Unit tests for tickwise.calendar.ics_feed."""

from __future__ import annotations

import re

import pytest

from tickwise.calendar.ics_feed import (
    FeedFilter,
    build_calendar,
    fetch_sessions_for_feed,
    generate_token,
)

SAMPLE_SESSIONS = [
    {
        "id": 1,
        "started_at": "2026-05-08T09:00:00",
        "ended_at": "2026-05-08T10:00:00",
        "duration_secs": 3600,
        "description": "Refactor capture loop",
        "project_name": "Tickwise",
        "project_color": "#3B82F6",
    },
    {
        "id": 2,
        "started_at": "2026-05-08T11:00:00",
        "ended_at": "2026-05-08T11:25:00",
        "duration_secs": 1500,
        "description": None,
        "project_name": None,
        "project_color": None,
    },
]


@pytest.mark.unit
class TestGenerateToken:
    def test_length_and_charset(self) -> None:
        token = generate_token()
        assert len(token) == 32
        assert re.fullmatch(r"[0-9a-f]+", token)

    def test_unique(self) -> None:
        assert generate_token() != generate_token()


@pytest.mark.unit
class TestBuildCalendar:
    def test_emits_vcalendar_envelope(self) -> None:
        out = build_calendar(SAMPLE_SESSIONS)
        assert "BEGIN:VCALENDAR" in out
        assert "END:VCALENDAR" in out
        assert "BEGIN:VEVENT" in out
        assert "tickwise-session-1@tickwise" in out

    def test_excludes_descriptions_by_default(self) -> None:
        out = build_calendar(SAMPLE_SESSIONS, include_descriptions=False)
        assert "Refactor capture loop" not in out

    def test_includes_descriptions_when_requested(self) -> None:
        out = build_calendar(SAMPLE_SESSIONS, include_descriptions=True)
        assert "Refactor capture loop" in out

    def test_session_with_no_project_uses_fallback_summary(self) -> None:
        out = build_calendar([SAMPLE_SESSIONS[1]])
        assert "Session #2" in out

    def test_open_session_skips_dtend(self) -> None:
        sessions = [{**SAMPLE_SESSIONS[0], "ended_at": None}]
        out = build_calendar(sessions)
        # The DTSTART is present but DTEND should not be.
        assert "DTSTART" in out
        assert "DTEND" not in out

    def test_manual_renderer_when_icalendar_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force the icalendar import path to fail.
        import builtins

        real_import = builtins.__import__

        def _raise(name: str, *a: object, **kw: object) -> object:
            if name == "icalendar":
                raise ImportError("not installed")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", _raise)
        out = build_calendar(SAMPLE_SESSIONS)
        assert "BEGIN:VCALENDAR" in out


@pytest.mark.unit
class TestFetchSessionsForFeed:
    def test_filters_by_min_duration(self, tmp_db) -> None:
        from tickwise.db.connection import transaction

        with transaction() as conn:
            conn.execute(
                "INSERT INTO sessions (started_at, ended_at, duration_secs) " "VALUES (?, ?, ?), (?, ?, ?)",
                (
                    "2026-05-08T09:00:00",
                    "2026-05-08T09:05:00",
                    300,
                    "2026-05-08T10:00:00",
                    "2026-05-08T11:00:00",
                    3600,
                ),
            )
        long_only = fetch_sessions_for_feed(FeedFilter(min_duration_secs=600))
        assert len(long_only) == 1
        assert long_only[0]["duration_secs"] == 3600

    def test_billable_only(self, tmp_db) -> None:
        from tickwise.db.connection import transaction

        with transaction() as conn:
            conn.execute(
                "INSERT INTO sessions (started_at, duration_secs, is_billed) " "VALUES (?, ?, ?), (?, ?, ?)",
                ("2026-05-08T09:00:00", 600, 0, "2026-05-08T10:00:00", 600, 1),
            )
        billable = fetch_sessions_for_feed(FeedFilter(billable_only=True))
        assert len(billable) == 1
