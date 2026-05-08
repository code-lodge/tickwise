"""Calendar feed, providers, and manual sync endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from tickwise.calendar.ics_feed import (
    FeedFilter,
    build_calendar,
    fetch_sessions_for_feed,
    generate_token,
)
from tickwise.calendar.sync_service import CalendarSyncService
from tickwise.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# ─── Public ICS feed (no auth — token in URL) ────────────────────────────


@router.get("/feed/{token}.ics", include_in_schema=False)
async def serve_feed(token: str) -> Response:
    """Return the iCalendar document for a given feed token."""
    row = (
        get_connection()
        .execute(
            "SELECT * FROM ics_feed_config WHERE token = ? AND is_active = 1",
            (token,),
        )
        .fetchone()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Feed not found or inactive")
    filt = FeedFilter(
        project_filter=row["project_filter"],
        billable_only=False,
        min_duration_secs=0,
        include_descriptions=bool(row["include_descriptions"]),
    )
    sessions = fetch_sessions_for_feed(filt)
    body = build_calendar(sessions, include_descriptions=filt.include_descriptions, calendar_name=row["name"])
    return Response(content=body, media_type="text/calendar; charset=utf-8")


# ─── ICS feed CRUD ───────────────────────────────────────────────────────


class FeedConfigIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    include_descriptions: bool = False
    project_filter: str | None = None
    is_active: bool = True


class FeedConfigOut(FeedConfigIn):
    id: int
    token: str


@router.get("/feeds", response_model=list[FeedConfigOut])
async def list_feeds() -> list[FeedConfigOut]:
    rows = get_connection().execute("SELECT * FROM ics_feed_config ORDER BY id").fetchall()
    return [FeedConfigOut(**_feed_row(row)) for row in rows]


@router.post("/feeds", response_model=FeedConfigOut, status_code=201)
async def create_feed(payload: FeedConfigIn) -> FeedConfigOut:
    token = generate_token()
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO ics_feed_config (name, token, include_descriptions, project_filter, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                token,
                1 if payload.include_descriptions else 0,
                payload.project_filter,
                1 if payload.is_active else 0,
            ),
        )
        feed_id = int(cur.lastrowid or 0)
    return FeedConfigOut(id=feed_id, token=token, **payload.model_dump())


@router.delete("/feeds/{feed_id}", status_code=204)
async def delete_feed(feed_id: int) -> None:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM ics_feed_config WHERE id = ?", (feed_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Feed {feed_id} not found")


# ─── ICS export (one-shot download) ──────────────────────────────────────


@router.get("/export.ics")
async def export_ics(
    project_filter: str | None = None,
    billable_only: bool = False,
    include_descriptions: bool = False,
) -> Response:
    filt = FeedFilter(
        project_filter=project_filter,
        billable_only=billable_only,
        min_duration_secs=0,
        include_descriptions=include_descriptions,
    )
    sessions = fetch_sessions_for_feed(filt)
    body = build_calendar(sessions, include_descriptions=include_descriptions)
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=tickwise.ics"},
    )


# ─── Provider CRUD ───────────────────────────────────────────────────────


class ProviderIn(BaseModel):
    name: str
    type: str = Field(pattern="^(caldav|google|ical)$")
    url: str | None = None
    username: str | None = None
    is_active: bool = True


class ProviderOut(ProviderIn):
    id: int
    last_synced_at: str | None = None


@router.get("/providers", response_model=list[ProviderOut])
async def list_providers() -> list[ProviderOut]:
    rows = get_connection().execute("SELECT * FROM calendar_providers ORDER BY id").fetchall()
    return [ProviderOut(**_provider_row(row)) for row in rows]


@router.post("/providers", response_model=ProviderOut, status_code=201)
async def create_provider(payload: ProviderIn) -> ProviderOut:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO calendar_providers (name, type, url, username, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.type,
                payload.url,
                payload.username,
                1 if payload.is_active else 0,
            ),
        )
        provider_id = int(cur.lastrowid or 0)
    return ProviderOut(id=provider_id, last_synced_at=None, **payload.model_dump())


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: int) -> None:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM calendar_providers WHERE id = ?", (provider_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")


# ─── Manual sync trigger ─────────────────────────────────────────────────


@router.post("/sync", response_model=list[dict[str, Any]])
async def run_sync_now() -> list[dict[str, Any]]:
    service = CalendarSyncService()
    reports = service.run_once()
    return [
        {
            "provider_id": r.provider_id,
            "provider_name": r.provider_name,
            "events_pushed": r.events_pushed,
            "events_updated": r.events_updated,
            "errors": r.errors,
        }
        for r in reports
    ]


# ─── helpers ─────────────────────────────────────────────────────────────


def _feed_row(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "token": row["token"],
        "name": row["name"],
        "include_descriptions": bool(row["include_descriptions"]),
        "project_filter": row["project_filter"],
        "is_active": bool(row["is_active"]),
    }


def _provider_row(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "type": row["type"],
        "url": row["url"],
        "username": row["username"],
        "is_active": bool(row["is_active"]),
        "last_synced_at": row["last_synced_at"],
    }
