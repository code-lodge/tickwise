"""Pomodoro lifecycle + history endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from tickwise import runtime
from tickwise.db.connection import get_connection
from tickwise.pomodoro.timer import (
    PomodoroSettings,
    PomodoroTimer,
    snapshot_to_dict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pomodoro", tags=["pomodoro"])


class SettingsPayload(BaseModel):
    work_minutes: int = Field(ge=1, le=180)
    short_break_minutes: int = Field(ge=1, le=60)
    long_break_minutes: int = Field(ge=1, le=120)
    cycles_before_long: int = Field(ge=1, le=12)
    auto_start: bool = False


def _timer() -> PomodoroTimer:
    timer = runtime.get_pomodoro_timer()
    if timer is None:
        # Lazy-create when running without the full app boot (tests, dev).
        # Started here too — under uvicorn-only boot nothing else would.
        timer = PomodoroTimer()
        timer.start_thread()
        runtime.set_pomodoro_timer(timer)
    return timer


@router.get("/status")
async def get_status() -> dict[str, Any]:
    return snapshot_to_dict(_timer().snapshot())


@router.get("/settings", response_model=SettingsPayload)
async def get_settings() -> SettingsPayload:
    s = _timer().settings
    return SettingsPayload(
        work_minutes=s.work_minutes,
        short_break_minutes=s.short_break_minutes,
        long_break_minutes=s.long_break_minutes,
        cycles_before_long=s.cycles_before_long,
        auto_start=s.auto_start,
    )


@router.put("/settings", response_model=SettingsPayload)
async def update_settings(payload: SettingsPayload) -> SettingsPayload:
    _timer().update_settings(
        PomodoroSettings(
            work_minutes=payload.work_minutes,
            short_break_minutes=payload.short_break_minutes,
            long_break_minutes=payload.long_break_minutes,
            cycles_before_long=payload.cycles_before_long,
            auto_start=payload.auto_start,
        )
    )
    return payload


@router.post("/start")
async def start(target: str = "focus") -> dict[str, Any]:
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


@router.post("/stop")
async def stop() -> dict[str, Any]:
    return snapshot_to_dict(_timer().stop())


@router.get("/history")
async def history(
    limit: int = Query(default=20, ge=1, le=200),
    type: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM pomodoro_sessions"
    params: list[Any] = []
    if type:
        sql += " WHERE type = ?"
        params.append(type)
    sql += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    rows = get_connection().execute(sql, params).fetchall()
    return [
        {
            "id": int(r["id"]),
            "type": r["type"],
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "completed": bool(r["completed"]),
        }
        for r in rows
    ]
