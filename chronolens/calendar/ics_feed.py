"""ICS (RFC 5545) feed + export generation.

Two consumers:

- The HTTP feed at ``GET /api/calendar/feed/{token}.ics`` produces a
  filtered live feed for URL-subscribing calendar clients (Tuta, Google,
  Apple Calendar, Outlook).
- The download endpoint emits the same payload as a one-off attachment.

Both code paths share `build_calendar()` so filters, summary text, and
description formatting stay in lockstep.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from chronolens.db.connection import get_connection

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FeedFilter:
    """Optional filters applied when generating a feed."""

    project_filter: str | None = None  # "1,2,3" — comma-separated project ids
    billable_only: bool = False
    min_duration_secs: int = 0
    include_descriptions: bool = False


def generate_token() -> str:
    """Return a 32-char hex token suitable for ICS feed URLs."""
    return secrets.token_hex(16)


def fetch_sessions_for_feed(filt: FeedFilter, *, limit: int = 5000) -> list[dict[str, Any]]:
    """Pull sessions matching the filter, joining project name + color."""
    clauses: list[str] = ["s.duration_secs >= ?"]
    params: list[Any] = [filt.min_duration_secs]
    if filt.billable_only:
        clauses.append("s.is_billed = 1")
    if filt.project_filter:
        ids = [s.strip() for s in filt.project_filter.split(",") if s.strip().isdigit()]
        if ids:
            placeholders = ", ".join("?" * len(ids))
            clauses.append(f"s.project_id IN ({placeholders})")
            params.extend(int(i) for i in ids)
    where = "WHERE " + " AND ".join(clauses)
    sql = f"""
        SELECT s.id, s.started_at, s.ended_at, s.duration_secs, s.description,
               p.name AS project_name, p.color AS project_color
          FROM sessions s
          LEFT JOIN projects p ON p.id = s.project_id
        {where}
         ORDER BY s.started_at DESC
         LIMIT ?
    """
    params.append(limit)
    rows = get_connection().execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def build_calendar(
    sessions: Iterable[dict[str, Any]],
    *,
    include_descriptions: bool = False,
    calendar_name: str = "ChronoLens",
) -> str:
    """Render an iCalendar document. Uses the `icalendar` library when
    available, with a hand-rolled RFC 5545 fallback so tests can run
    without the library installed.
    """
    sessions_list = list(sessions)
    try:
        return _build_with_icalendar(sessions_list, include_descriptions, calendar_name)
    except ImportError:
        return _build_manual(sessions_list, include_descriptions, calendar_name)


def _build_with_icalendar(sessions: list[dict[str, Any]], include_descriptions: bool, calendar_name: str) -> str:
    from icalendar import Calendar, Event

    cal = Calendar()
    cal.add("prodid", "-//ChronoLens//chronolens//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", calendar_name)
    cal.add("method", "PUBLISH")
    for row in sessions:
        event = Event()
        event.add("uid", f"chronolens-session-{row['id']}@chronolens")
        event.add("summary", _summary(row, include_description=include_descriptions))
        event.add("dtstart", _parse_iso(row["started_at"]))
        ended = row.get("ended_at")
        if ended:
            event.add("dtend", _parse_iso(ended))
        event.add("dtstamp", datetime.now(tz=UTC))
        if include_descriptions and row.get("description"):
            event.add("description", row["description"])
        if row.get("project_color"):
            event.add("color", row["project_color"])
        cal.add_component(event)
    return str(cal.to_ical().decode("utf-8"))


def _build_manual(sessions: list[dict[str, Any]], include_descriptions: bool, calendar_name: str) -> str:
    """Pure-stdlib RFC 5545 generator (used when icalendar isn't installed)."""
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ChronoLens//chronolens//EN",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
        "METHOD:PUBLISH",
    ]
    now = _format_dt(datetime.now(tz=UTC))
    for row in sessions:
        ended = row.get("ended_at")
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:chronolens-session-{row['id']}@chronolens")
        lines.append(f"SUMMARY:{_escape(_summary(row, include_description=include_descriptions))}")
        lines.append(f"DTSTART:{_format_dt(_parse_iso(row['started_at']))}")
        if ended:
            lines.append(f"DTEND:{_format_dt(_parse_iso(ended))}")
        lines.append(f"DTSTAMP:{now}")
        if include_descriptions and row.get("description"):
            lines.append(f"DESCRIPTION:{_escape(row['description'])}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _summary(row: dict[str, Any], *, include_description: bool = False) -> str:
    parts = []
    if row.get("project_name"):
        parts.append(row["project_name"])
    if include_description and row.get("description"):
        parts.append(row["description"])
    return " — ".join(parts) or f"Session #{row['id']}"


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
