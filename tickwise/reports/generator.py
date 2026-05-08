"""Aggregate session data into report shapes the API can serialize.

Five report types per spec §10:

- ``summary``       — total hours per project for a date range, optionally
                      grouped by day / week / month.
- ``billing``       — hours × hourly rate per project with billable
                      vs non-billable totals.
- ``activity``      — distribution across task categories.
- ``detailed``      — full session list with timestamps.
- ``productivity``  — active vs idle, most productive hours,
                      pomodoro completion rate.

Each returns a plain dict so the API can pass it straight through to
JSON serialization or to one of the export modules (CSV / PDF).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from tickwise.db.connection import get_connection

logger = logging.getLogger(__name__)


GroupBy = Literal["day", "week", "month"]
ReportType = Literal["summary", "billing", "activity", "detailed", "productivity"]


@dataclass(slots=True)
class ReportRequest:
    type: ReportType
    from_date: str  # ISO date or datetime
    to_date: str
    project_ids: list[int] = field(default_factory=list)
    group_by: GroupBy = "day"


# ─── public dispatcher ───────────────────────────────────────────────────


def generate(request: ReportRequest) -> dict[str, Any]:
    """Return a dict shaped for the matching report type."""
    if request.type == "summary":
        return _time_summary(request)
    if request.type == "billing":
        return _billing(request)
    if request.type == "activity":
        return _activity(request)
    if request.type == "detailed":
        return _detailed(request)
    if request.type == "productivity":
        return _productivity(request)
    raise ValueError(f"unknown report type: {request.type}")


# ─── individual reports ──────────────────────────────────────────────────


def _time_summary(request: ReportRequest) -> dict[str, Any]:
    rows = _fetch_sessions(request)
    buckets: dict[tuple[str, str | None], int] = defaultdict(int)
    project_totals: dict[str, int] = defaultdict(int)
    for row in rows:
        bucket = _bucket(row["started_at"], request.group_by)
        project = row["project_name"] or "Unclassified"
        buckets[(bucket, project)] += int(row["duration_secs"] or 0)
        project_totals[project] += int(row["duration_secs"] or 0)
    series = [
        {"bucket": bucket, "project": project, "seconds": secs} for (bucket, project), secs in sorted(buckets.items())
    ]
    return {
        "type": "summary",
        "from": request.from_date,
        "to": request.to_date,
        "group_by": request.group_by,
        "by_project": [{"project": p, "seconds": s} for p, s in sorted(project_totals.items(), key=lambda kv: -kv[1])],
        "series": series,
        "total_seconds": sum(project_totals.values()),
    }


def _billing(request: ReportRequest) -> dict[str, Any]:
    rows = _fetch_sessions(request, include_rate=True)
    totals: dict[str, dict[str, Any]] = {}
    grand_billable = 0.0
    grand_non_billable_secs = 0
    for row in rows:
        project = row["project_name"] or "Unclassified"
        rate = float(row["hourly_rate"] or 0.0)
        secs = int(row["duration_secs"] or 0)
        hours = secs / 3600.0
        amount = hours * rate
        bucket = totals.setdefault(
            project,
            {
                "project": project,
                "currency": row["currency"] or "USD",
                "billable_seconds": 0,
                "non_billable_seconds": 0,
                "amount": 0.0,
                "rate": rate,
            },
        )
        if row["is_billed"]:
            bucket["billable_seconds"] += secs
            bucket["amount"] += amount
            grand_billable += amount
        else:
            bucket["non_billable_seconds"] += secs
            grand_non_billable_secs += secs
    return {
        "type": "billing",
        "from": request.from_date,
        "to": request.to_date,
        "by_project": list(totals.values()),
        "grand_total_amount": round(grand_billable, 2),
        "non_billable_seconds": grand_non_billable_secs,
    }


def _activity(request: ReportRequest) -> dict[str, Any]:
    sql = """
        SELECT COALESCE(c.name, 'Uncategorised') AS category,
               COALESCE(p.name, 'Unclassified') AS project,
               SUM(s.duration_secs) AS seconds,
               COUNT(*) AS sessions
          FROM sessions s
          LEFT JOIN task_categories c ON c.id = s.category_id
          LEFT JOIN projects p ON p.id = s.project_id
         WHERE s.started_at >= ? AND s.started_at <= ?
         GROUP BY c.name, p.name
         ORDER BY seconds DESC
    """
    rows = get_connection().execute(sql, (_start_of(request.from_date), _end_of(request.to_date))).fetchall()
    return {
        "type": "activity",
        "from": request.from_date,
        "to": request.to_date,
        "rows": [
            {
                "category": row["category"],
                "project": row["project"],
                "seconds": int(row["seconds"] or 0),
                "sessions": int(row["sessions"]),
            }
            for row in rows
        ],
    }


def _detailed(request: ReportRequest) -> dict[str, Any]:
    rows = _fetch_sessions(request)
    return {
        "type": "detailed",
        "from": request.from_date,
        "to": request.to_date,
        "sessions": [
            {
                "id": int(row["id"]),
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "duration_secs": int(row["duration_secs"] or 0),
                "project": row["project_name"],
                "description": row["description"],
                "is_billed": bool(row["is_billed"]),
            }
            for row in rows
        ],
    }


def _productivity(request: ReportRequest) -> dict[str, Any]:
    rows = _fetch_sessions(request)
    by_hour: dict[int, int] = defaultdict(int)
    total = 0
    classified = 0
    for row in rows:
        secs = int(row["duration_secs"] or 0)
        total += secs
        if row["llm_classified"]:
            classified += secs
        if row["started_at"]:
            hour = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00")).hour
            by_hour[hour] += secs

    pomo = (
        get_connection()
        .execute(
            """
            SELECT type AS pomo_type,
                   COUNT(*) AS total,
                   SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed
              FROM pomodoro_sessions
             WHERE started_at >= ? AND started_at <= ?
             GROUP BY type
            """,
            (_start_of(request.from_date), _end_of(request.to_date)),
        )
        .fetchall()
    )

    return {
        "type": "productivity",
        "from": request.from_date,
        "to": request.to_date,
        "active_seconds": total,
        "classified_seconds": classified,
        "active_by_hour": [{"hour": h, "seconds": by_hour.get(h, 0)} for h in range(24)],
        "pomodoro": [
            {
                "type": row["pomo_type"],
                "total": int(row["total"]),
                "completed": int(row["completed"] or 0),
            }
            for row in pomo
        ],
    }


# ─── helpers ──────────────────────────────────────────────────────────────


def _fetch_sessions(request: ReportRequest, *, include_rate: bool = False) -> list[dict[str, Any]]:
    rate_cols = ", p.hourly_rate, p.currency" if include_rate else ""
    project_filter = ""
    params: list[Any] = [_start_of(request.from_date), _end_of(request.to_date)]
    if request.project_ids:
        placeholders = ", ".join("?" * len(request.project_ids))
        project_filter = f" AND s.project_id IN ({placeholders})"
        params.extend(request.project_ids)
    sql = f"""
        SELECT s.id, s.started_at, s.ended_at, s.duration_secs, s.description,
               s.is_billed, s.llm_classified,
               p.name AS project_name{rate_cols}
          FROM sessions s
          LEFT JOIN projects p ON p.id = s.project_id
         WHERE s.started_at >= ? AND s.started_at <= ?
           {project_filter}
         ORDER BY s.started_at
    """
    return [dict(row) for row in get_connection().execute(sql, params).fetchall()]


def _bucket(started_at: str, group_by: GroupBy) -> str:
    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00")).astimezone(UTC)
    if group_by == "day":
        return dt.strftime("%Y-%m-%d")
    if group_by == "week":
        # ISO week — Monday of that week.
        start_of_week = dt - timedelta(days=dt.weekday())
        return start_of_week.strftime("%Y-W%V")
    return dt.strftime("%Y-%m")


def _start_of(value: str) -> str:
    """Coerce date-or-datetime into the SQL-comparable lower bound."""
    if "T" in value:
        return value
    return f"{value}T00:00:00"


def _end_of(value: str) -> str:
    if "T" in value:
        return value
    return f"{value}T23:59:59"
