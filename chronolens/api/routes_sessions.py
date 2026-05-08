"""Session read endpoints: GET /api/sessions and GET /api/sessions/{id}."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from chronolens.db.connection import transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


@router.get("", response_model=list[dict[str, Any]])
async def list_sessions(
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """Return sessions ordered by start time descending.

    Accepts ISO-8601 `from` and `to` timestamps; both are optional and
    matched against `started_at`. The default page size is 200; pagination
    by start cursor will be added in Phase 4 once the dashboard needs it.
    """
    clauses: list[str] = []
    params: list[Any] = []
    if from_:
        clauses.append("started_at >= ?")
        params.append(from_)
    if to:
        clauses.append("started_at <= ?")
        params.append(to)
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
