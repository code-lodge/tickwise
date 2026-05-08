"""Session endpoints: list, get, edit, split, merge."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from chronolens.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


class SessionUpdate(BaseModel):
    """Mutable fields callers can change on a session."""

    project_id: int | None = None
    category_id: int | None = None
    description: str | None = None
    tags: str | None = None
    is_billed: bool | None = None
    is_manual: bool | None = None


class SessionSplit(BaseModel):
    """Split a session in two at the given ISO-8601 timestamp."""

    split_at: str = Field(description="ISO-8601 timestamp inside [started_at, ended_at]")


class SessionMerge(BaseModel):
    """Merge two existing sessions into one (target absorbs source)."""

    other_id: int


@router.get("", response_model=list[dict[str, Any]])
async def list_sessions(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """Return sessions ordered by start time descending."""
    clauses: list[str] = []
    params: list[Any] = []
    if from_:
        clauses.append("started_at >= ?")
        params.append(from_)
    if to:
        clauses.append("started_at <= ?")
        params.append(to)
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM sessions {where} ORDER BY started_at DESC LIMIT ?"
    params.append(limit)
    with transaction() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_dict(row) for row in rows]


@router.get("/{session_id}", response_model=dict[str, Any])
async def get_session(session_id: int) -> dict[str, Any]:
    """Return a single session by id, or 404 if it doesn't exist."""
    with transaction() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return _row_to_dict(row)


@router.put("/{session_id}", response_model=dict[str, Any])
async def update_session(session_id: int, payload: SessionUpdate) -> dict[str, Any]:
    """Patch any subset of `SessionUpdate` fields onto an existing session.

    Fields not present on the payload (None) are left unchanged. The row's
    `updated_at` is bumped on every successful call.
    """
    fields: list[str] = []
    params: list[Any] = []
    data = payload.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=422, detail="No fields to update")
    for key, value in data.items():
        if isinstance(value, bool):
            value = 1 if value else 0
        fields.append(f"{key} = ?")
        params.append(value)
    fields.append("updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')")
    params.append(session_id)
    with transaction() as conn:
        cur = conn.execute(
            f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return await get_session(session_id)


@router.post("/{session_id}/split", response_model=list[dict[str, Any]])
async def split_session(session_id: int, payload: SessionSplit) -> list[dict[str, Any]]:
    """Cut one session into two at `split_at`. Returns both new rows.

    The original session keeps its id and gets `ended_at = split_at`; the
    second half is inserted as a new row that inherits classification.
    """
    try:
        split_dt = datetime.fromisoformat(payload.split_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid split_at: {exc}") from exc

    with transaction() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        started = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
        ended = datetime.fromisoformat(row["ended_at"].replace("Z", "+00:00")) if row["ended_at"] else None
        if split_dt <= started or (ended is not None and split_dt >= ended):
            raise HTTPException(
                status_code=422,
                detail="split_at must be strictly inside the session's time range",
            )

        first_duration = int((split_dt - started).total_seconds())
        second_duration = int((ended - split_dt).total_seconds()) if ended is not None else None
        split_iso = split_dt.isoformat()

        # Truncate the original.
        conn.execute(
            "UPDATE sessions SET ended_at = ?, duration_secs = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (split_iso, first_duration, session_id),
        )
        # Insert the second half, copying classification.
        cur = conn.execute(
            """
            INSERT INTO sessions
                (started_at, ended_at, duration_secs, project_id, category_id,
                 description, tags, is_manual, is_billed, llm_classified, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                split_iso,
                row["ended_at"],
                second_duration,
                row["project_id"],
                row["category_id"],
                row["description"],
                row["tags"],
                row["is_manual"],
                row["is_billed"],
                row["llm_classified"],
                row["confidence"],
            ),
        )
        new_id = int(cur.lastrowid or 0)

    first = await get_session(session_id)
    second = await get_session(new_id)
    return [first, second]


@router.post("/{session_id}/merge", response_model=dict[str, Any])
async def merge_sessions(session_id: int, payload: SessionMerge) -> dict[str, Any]:
    """Merge `other_id` into `session_id`. Source row is deleted on success."""
    if payload.other_id == session_id:
        raise HTTPException(status_code=422, detail="Cannot merge a session with itself")

    with transaction() as conn:
        rows = conn.execute("SELECT * FROM sessions WHERE id IN (?, ?)", (session_id, payload.other_id)).fetchall()
        if len(rows) != 2:
            raise HTTPException(status_code=404, detail="One or both sessions not found")
        target = next(r for r in rows if r["id"] == session_id)
        source = next(r for r in rows if r["id"] == payload.other_id)

        new_started = min(target["started_at"], source["started_at"])
        if target["ended_at"] is None or source["ended_at"] is None:
            new_ended = target["ended_at"] or source["ended_at"]
        else:
            new_ended = max(target["ended_at"], source["ended_at"])
        new_duration = (target["duration_secs"] or 0) + (source["duration_secs"] or 0)

        conn.execute(
            """
            UPDATE sessions
               SET started_at = ?, ended_at = ?, duration_secs = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE id = ?
            """,
            (new_started, new_ended, new_duration, session_id),
        )
        conn.execute("DELETE FROM sessions WHERE id = ?", (payload.other_id,))
    return await get_session(session_id)


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: int) -> None:
    """Hard-delete a session. Useful for the dashboard's bulk cleanup tools."""
    with transaction() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@router.get("/summary/today", response_model=dict[str, Any])
async def today_summary() -> dict[str, Any]:
    """Aggregate stats for the Live View card."""
    conn = get_connection()
    summary = conn.execute("""
        SELECT COALESCE(SUM(duration_secs), 0) AS total,
               COALESCE(SUM(CASE WHEN is_billed = 1 THEN duration_secs END), 0) AS billable,
               COUNT(*) AS sessions,
               COUNT(CASE WHEN project_id IS NULL THEN 1 END) AS unclassified
          FROM sessions
         WHERE started_at >= strftime('%Y-%m-%dT00:00:00Z', 'now')
        """).fetchone()
    by_project = conn.execute("""
        SELECT p.name AS name, p.color AS color, SUM(s.duration_secs) AS seconds
          FROM sessions s
          LEFT JOIN projects p ON p.id = s.project_id
         WHERE s.started_at >= strftime('%Y-%m-%dT00:00:00Z', 'now')
         GROUP BY s.project_id
         ORDER BY seconds DESC
        """).fetchall()
    return {
        "total_seconds": int(summary["total"]),
        "billable_seconds": int(summary["billable"]),
        "session_count": int(summary["sessions"]),
        "unclassified_count": int(summary["unclassified"]),
        "by_project": [
            {
                "name": row["name"] or "Unclassified",
                "color": row["color"] or "#9CA3AF",
                "seconds": int(row["seconds"] or 0),
            }
            for row in by_project
        ],
    }
