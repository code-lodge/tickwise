"""Mobile-companion endpoints — bearer-authenticated.

The PWA running on the user's phone hits these via the Cloudflare
Tunnel ingress. Every endpoint requires a valid bearer token issued
through the dashboard pairing flow.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from tickwise import runtime
from tickwise.api.auth import TokenInfo, require_bearer_token
from tickwise.db.connection import get_connection
from tickwise.pomodoro.timer import (
    PomodoroSettings,
    PomodoroTimer,
    snapshot_to_dict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mobile", tags=["mobile"])

_AUTH = Depends(require_bearer_token)


def _timer() -> PomodoroTimer:
    timer = runtime.get_pomodoro_timer()
    if timer is None:
        timer = PomodoroTimer()
        runtime.set_pomodoro_timer(timer)
    return timer


@router.get("/whoami")
async def whoami(token: TokenInfo = _AUTH) -> dict[str, Any]:
    """Confirm the token is valid and identify the device."""
    return {
        "token_id": token.id,
        "device_name": token.device_name,
        "created_at": token.created_at,
        "last_used": token.last_used,
    }


@router.get("/status")
async def mobile_status(_: TokenInfo = _AUTH) -> dict[str, Any]:
    loop = runtime.get_capture_loop()
    tracking = bool(loop and loop.is_running and not loop.is_paused)
    timer = runtime.get_pomodoro_timer()
    return {
        "tracking": tracking,
        "pomodoro": snapshot_to_dict(timer.snapshot()) if timer else None,
    }


@router.get("/today")
async def today(_: TokenInfo = _AUTH) -> dict[str, Any]:
    today_iso = date.today().isoformat()
    rows = (
        get_connection()
        .execute(
            """
        SELECT s.duration_secs, s.is_billed, p.name AS project_name, p.color AS project_color
          FROM sessions s
          LEFT JOIN projects p ON p.id = s.project_id
         WHERE date(s.started_at) = date(?)
           AND s.duration_secs IS NOT NULL
        """,
            (today_iso,),
        )
        .fetchall()
    )
    total = sum(int(r["duration_secs"] or 0) for r in rows)
    billable = sum(int(r["duration_secs"] or 0) for r in rows if r["is_billed"])
    by_project: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = r["project_name"] or "Unassigned"
        bucket = by_project.setdefault(
            key,
            {"name": key, "color": r["project_color"] or "#9CA3AF", "seconds": 0},
        )
        bucket["seconds"] += int(r["duration_secs"] or 0)
    return {
        "date": today_iso,
        "total_seconds": total,
        "billable_seconds": billable,
        "session_count": len(rows),
        "by_project": sorted(by_project.values(), key=lambda b: -b["seconds"]),
    }


@router.get("/timeline")
async def timeline(
    days: int = Query(default=1, ge=1, le=14),
    _: TokenInfo = _AUTH,
) -> list[dict[str, Any]]:
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = (
        get_connection()
        .execute(
            """
        SELECT s.id, s.started_at, s.ended_at, s.duration_secs, s.description,
               p.name AS project_name, p.color AS project_color
          FROM sessions s
          LEFT JOIN projects p ON p.id = s.project_id
         WHERE date(s.started_at) >= date(?)
         ORDER BY s.started_at DESC
         LIMIT 200
        """,
            (start,),
        )
        .fetchall()
    )
    return [
        {
            "id": int(r["id"]),
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "duration_secs": int(r["duration_secs"] or 0),
            "description": r["description"],
            "project_name": r["project_name"],
            "project_color": r["project_color"],
        }
        for r in rows
    ]


@router.get("/projects")
async def mobile_projects(_: TokenInfo = _AUTH) -> list[dict[str, Any]]:
    rows = (
        get_connection()
        .execute("SELECT id, name, color, hourly_rate, currency FROM projects WHERE is_active = 1 ORDER BY name")
        .fetchall()
    )
    return [
        {
            "id": int(r["id"]),
            "name": r["name"],
            "color": r["color"],
            "hourly_rate": r["hourly_rate"],
            "currency": r["currency"],
        }
        for r in rows
    ]


@router.get("/pomodoro/status")
async def pomodoro_status(_: TokenInfo = _AUTH) -> dict[str, Any]:
    return snapshot_to_dict(_timer().snapshot())


@router.post("/pomodoro/start")
async def pomodoro_start(
    target: str = "focus",
    _: TokenInfo = _AUTH,
) -> dict[str, Any]:
    timer = _timer()
    if target == "focus":
        snap = timer.start_focus()
    elif target == "short_break":
        snap = timer.start_short_break()
    elif target == "long_break":
        snap = timer.start_long_break()
    else:
        raise HTTPException(status_code=422, detail=f"unknown target: {target}")
    return snapshot_to_dict(snap)


@router.post("/pomodoro/stop")
async def pomodoro_stop(_: TokenInfo = _AUTH) -> dict[str, Any]:
    return snapshot_to_dict(_timer().stop())


@router.put("/pomodoro/settings")
async def pomodoro_update_settings(
    payload: dict[str, Any],
    _: TokenInfo = _AUTH,
) -> dict[str, Any]:
    s = PomodoroSettings(
        work_minutes=int(payload.get("work_minutes", 25)),
        short_break_minutes=int(payload.get("short_break_minutes", 5)),
        long_break_minutes=int(payload.get("long_break_minutes", 15)),
        cycles_before_long=int(payload.get("cycles_before_long", 4)),
        auto_start=bool(payload.get("auto_start", False)),
    )
    _timer().update_settings(s)
    return {
        "work_minutes": s.work_minutes,
        "short_break_minutes": s.short_break_minutes,
        "long_break_minutes": s.long_break_minutes,
        "cycles_before_long": s.cycles_before_long,
        "auto_start": s.auto_start,
    }
