"""Redaction-engine endpoints: level get/set, custom rule CRUD, preview."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from chronolens.db.connection import get_connection, transaction
from chronolens.redaction.custom_rules import CustomRule
from chronolens.redaction.engine import RedactionEngine
from chronolens.redaction.levels import LEVEL_DESCRIPTIONS, categories_for_level

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/redaction", tags=["redaction"])


# ─── level ──────────────────────────────────────────────────────────────


class LevelPayload(BaseModel):
    level: int = Field(ge=1, le=4)


class LevelInfo(BaseModel):
    level: int
    description: str
    categories: list[str]


@router.get("/level", response_model=LevelInfo)
async def get_level() -> LevelInfo:
    row = get_connection().execute("SELECT value FROM settings WHERE key = 'privacy_level'").fetchone()
    level = int(row["value"]) if row else 2
    return LevelInfo(
        level=level,
        description=LEVEL_DESCRIPTIONS.get(level, ""),
        categories=categories_for_level(level),
    )


@router.put("/level", response_model=LevelInfo)
async def set_level(payload: LevelPayload) -> LevelInfo:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('privacy_level', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ', 'now')",
            (str(payload.level),),
        )
    return await get_level()


# ─── custom rules ───────────────────────────────────────────────────────


class CustomRuleIn(BaseModel):
    pattern: str = Field(min_length=1)
    match_mode: Literal["contains", "regex", "exact"] = "contains"
    replacement: str = "[REDACTED]"
    description: str | None = None
    is_active: bool = True


class CustomRuleOut(CustomRuleIn):
    id: int


def _row_to_rule(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "pattern": row["pattern"],
        "match_mode": row["match_mode"] or "contains",
        "replacement": row["replacement"] or "[REDACTED]",
        "description": row["description"],
        "is_active": bool(row["is_active"]),
    }


@router.get("/rules", response_model=list[CustomRuleOut])
async def list_rules() -> list[CustomRuleOut]:
    rows = get_connection().execute("SELECT * FROM custom_redaction_rules ORDER BY id").fetchall()
    return [CustomRuleOut(**_row_to_rule(row)) for row in rows]


@router.post("/rules", response_model=CustomRuleOut, status_code=201)
async def create_rule(payload: CustomRuleIn) -> CustomRuleOut:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO custom_redaction_rules
                (pattern, match_mode, replacement, description, is_active, is_regex)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.pattern,
                payload.match_mode,
                payload.replacement,
                payload.description,
                1 if payload.is_active else 0,
                1 if payload.match_mode == "regex" else 0,
            ),
        )
        rule_id = int(cur.lastrowid or 0)
    return CustomRuleOut(id=rule_id, **payload.model_dump())


@router.put("/rules/{rule_id}", response_model=CustomRuleOut)
async def update_rule(rule_id: int, payload: CustomRuleIn) -> CustomRuleOut:
    with transaction() as conn:
        cur = conn.execute(
            """
            UPDATE custom_redaction_rules
               SET pattern = ?, match_mode = ?, replacement = ?,
                   description = ?, is_active = ?, is_regex = ?
             WHERE id = ?
            """,
            (
                payload.pattern,
                payload.match_mode,
                payload.replacement,
                payload.description,
                1 if payload.is_active else 0,
                1 if payload.match_mode == "regex" else 0,
                rule_id,
            ),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return CustomRuleOut(id=rule_id, **payload.model_dump())


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: int) -> None:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM custom_redaction_rules WHERE id = ?", (rule_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")


# ─── preview ────────────────────────────────────────────────────────────


class PreviewRequest(BaseModel):
    text: str
    level: int = Field(default=2, ge=1, le=4)


class PreviewResponse(BaseModel):
    redacted_text: str
    original_length: int
    redacted_length: int
    redaction_count: int
    categories_hit: list[str]


@router.post("/preview", response_model=PreviewResponse)
async def preview(payload: PreviewRequest) -> PreviewResponse:
    rules = [
        CustomRule(
            pattern=r["pattern"],
            match_mode=r["match_mode"] or "contains",
            replacement=r["replacement"] or "[REDACTED]",
        )
        for r in (
            get_connection()
            .execute("SELECT pattern, match_mode, replacement FROM custom_redaction_rules " "WHERE is_active = 1")
            .fetchall()
        )
    ]
    engine = RedactionEngine(payload.level, custom_rules=rules)
    out = engine.redact(payload.text)
    return PreviewResponse(
        redacted_text=out.redacted_text,
        original_length=out.original_length,
        redacted_length=out.redacted_length,
        redaction_count=out.redaction_count,
        categories_hit=out.categories_hit,
    )
