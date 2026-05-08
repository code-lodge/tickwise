"""Projects CRUD endpoints — drives the dashboard's Projects page."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tickwise.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    color: str = "#3B82F6"
    client_id: int | None = None
    hourly_rate: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    is_active: bool = True


class ProjectOut(ProjectIn):
    id: int
    total_seconds: int = 0


def _row_to_dict(row: Any, total_seconds: int = 0) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "color": row["color"],
        "client_id": row["client_id"],
        "hourly_rate": row["hourly_rate"],
        "currency": row["currency"],
        "is_active": bool(row["is_active"]),
        "total_seconds": int(total_seconds),
    }


@router.get("", response_model=list[ProjectOut])
async def list_projects(active_only: bool = False) -> list[ProjectOut]:
    """List projects with their cumulative tracked-time totals."""
    where = "WHERE p.is_active = 1" if active_only else ""
    rows = get_connection().execute(f"""
            SELECT p.*, COALESCE(SUM(s.duration_secs), 0) AS total_seconds
              FROM projects p
              LEFT JOIN sessions s ON s.project_id = p.id
              {where}
             GROUP BY p.id
             ORDER BY p.name
            """).fetchall()
    return [ProjectOut(**_row_to_dict(row, row["total_seconds"])) for row in rows]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int) -> ProjectOut:
    row = (
        get_connection()
        .execute(
            """
            SELECT p.*, COALESCE(SUM(s.duration_secs), 0) AS total_seconds
              FROM projects p
              LEFT JOIN sessions s ON s.project_id = p.id
             WHERE p.id = ?
             GROUP BY p.id
            """,
            (project_id,),
        )
        .fetchone()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return ProjectOut(**_row_to_dict(row, row["total_seconds"]))


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(payload: ProjectIn) -> ProjectOut:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO projects (name, color, client_id, hourly_rate, currency, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.color,
                payload.client_id,
                payload.hourly_rate,
                payload.currency,
                1 if payload.is_active else 0,
            ),
        )
        project_id = int(cur.lastrowid or 0)
    return await get_project(project_id)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: int, payload: ProjectIn) -> ProjectOut:
    with transaction() as conn:
        cur = conn.execute(
            """
            UPDATE projects
               SET name = ?, color = ?, client_id = ?, hourly_rate = ?,
                   currency = ?, is_active = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE id = ?
            """,
            (
                payload.name,
                payload.color,
                payload.client_id,
                payload.hourly_rate,
                payload.currency,
                1 if payload.is_active else 0,
                project_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return await get_project(project_id)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int) -> None:
    """Soft-delete: marks the project inactive, preserving session history."""
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE projects SET is_active = 0, " "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (project_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
