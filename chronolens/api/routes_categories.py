"""Task category CRUD — drives the dashboard's category dropdowns."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from chronolens.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = "#6B7280"
    project_id: int | None = None


class CategoryOut(CategoryIn):
    id: int


def _row(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "color": row["color"],
        "project_id": row["project_id"],
    }


@router.get("", response_model=list[CategoryOut])
async def list_categories(project_id: int | None = None) -> list[CategoryOut]:
    if project_id is not None:
        rows = (
            get_connection()
            .execute(
                "SELECT * FROM task_categories WHERE project_id = ? OR project_id IS NULL ORDER BY name",
                (project_id,),
            )
            .fetchall()
        )
    else:
        rows = get_connection().execute("SELECT * FROM task_categories ORDER BY name").fetchall()
    return [CategoryOut(**_row(row)) for row in rows]


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(payload: CategoryIn) -> CategoryOut:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO task_categories (name, color, project_id) VALUES (?, ?, ?)",
            (payload.name, payload.color, payload.project_id),
        )
        category_id = int(cur.lastrowid or 0)
    return CategoryOut(id=category_id, **payload.model_dump())


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(category_id: int, payload: CategoryIn) -> CategoryOut:
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE task_categories SET name = ?, color = ?, project_id = ? WHERE id = ?",
            (payload.name, payload.color, payload.project_id, category_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    return CategoryOut(id=category_id, **payload.model_dump())


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int) -> None:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM task_categories WHERE id = ?", (category_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
