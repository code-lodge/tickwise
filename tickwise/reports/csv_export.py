"""CSV exports for the five report types.

Each function writes a header row + one data row per record so the
output opens cleanly in Excel / Numbers / Google Sheets.
"""

from __future__ import annotations

import csv
import io
from typing import Any


def to_csv(report: dict[str, Any]) -> str:
    """Dispatch on `report["type"]` and return the rendered CSV string."""
    rtype = report.get("type")
    if rtype == "summary":
        return _summary_csv(report)
    if rtype == "billing":
        return _billing_csv(report)
    if rtype == "activity":
        return _activity_csv(report)
    if rtype == "detailed":
        return _detailed_csv(report)
    if rtype == "productivity":
        return _productivity_csv(report)
    raise ValueError(f"unsupported report type for CSV: {rtype}")


def _summary_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["bucket", "project", "hours"])
    for row in report.get("series", []):
        writer.writerow([row["bucket"], row["project"], round(row["seconds"] / 3600.0, 2)])
    writer.writerow([])
    writer.writerow(["project", "total_hours"])
    for row in report.get("by_project", []):
        writer.writerow([row["project"], round(row["seconds"] / 3600.0, 2)])
    return buf.getvalue()


def _billing_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["project", "currency", "billable_hours", "non_billable_hours", "rate", "amount"])
    for row in report.get("by_project", []):
        writer.writerow(
            [
                row["project"],
                row["currency"],
                round(row["billable_seconds"] / 3600.0, 2),
                round(row["non_billable_seconds"] / 3600.0, 2),
                row["rate"],
                round(row["amount"], 2),
            ]
        )
    return buf.getvalue()


def _activity_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["category", "project", "hours", "sessions"])
    for row in report.get("rows", []):
        writer.writerow(
            [
                row["category"],
                row["project"],
                round(row["seconds"] / 3600.0, 2),
                row["sessions"],
            ]
        )
    return buf.getvalue()


def _detailed_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["session_id", "started_at", "ended_at", "duration_hours", "project", "description", "is_billed"])
    for row in report.get("sessions", []):
        writer.writerow(
            [
                row["id"],
                row["started_at"],
                row["ended_at"],
                round(row["duration_secs"] / 3600.0, 2),
                row["project"] or "",
                row["description"] or "",
                "yes" if row["is_billed"] else "no",
            ]
        )
    return buf.getvalue()


def _productivity_csv(report: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["hour", "active_hours"])
    for row in report.get("active_by_hour", []):
        writer.writerow([row["hour"], round(row["seconds"] / 3600.0, 2)])
    writer.writerow([])
    writer.writerow(["pomodoro_type", "total", "completed"])
    for row in report.get("pomodoro", []):
        writer.writerow([row["type"], row["total"], row["completed"]])
    return buf.getvalue()
