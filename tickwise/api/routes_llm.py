"""LLM configuration, usage, and test-classify endpoints."""

from __future__ import annotations

import dataclasses
import logging
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tickwise.classification.claude_client import ClaudeClient
from tickwise.classification.cost_tracker import current_budget_state
from tickwise.classification.llm_client import LLMError
from tickwise.classification.openai_client import OpenAIClient
from tickwise.classification.pipeline import ClassificationPipeline
from tickwise.classification.prompts import (
    SYSTEM_PROMPT,
    ClassificationContext,
    build_user_prompt,
)
from tickwise.classification.queue import ClassificationJob
from tickwise.crypto import keyring
from tickwise.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])

_API_KEY_REF = "llm_api_key"


class LLMConfigPayload(BaseModel):
    """User-facing view of `llm_config` (api_key write-only)."""

    provider: Literal["anthropic", "openai"] = "anthropic"
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    monthly_budget_cents: int = Field(default=0, ge=0)
    is_active: bool = True
    api_key: str | None = None  # write-only
    has_api_key: bool = False  # read-only convenience flag


class LLMTestRequest(BaseModel):
    """Tiny payload that exercises the full classification pipeline."""

    process_name: str = "code.exe"
    window_title: str = "Tickwise — main.py"
    ocr_text: str = "def hello(): print('hi')"


@router.get("/config", response_model=LLMConfigPayload)
async def get_config() -> LLMConfigPayload:
    """Return the current LLM configuration (without leaking the API key)."""
    row = (
        get_connection()
        .execute(
            "SELECT provider, model, max_tokens, temperature, "
            "monthly_budget_cents, is_active, api_key_ref FROM llm_config WHERE id = 1"
        )
        .fetchone()
    )
    if row is None:
        return LLMConfigPayload()
    return LLMConfigPayload(
        provider=row["provider"],
        model=row["model"],
        max_tokens=int(row["max_tokens"]),
        temperature=float(row["temperature"]),
        monthly_budget_cents=int(row["monthly_budget_cents"]),
        is_active=bool(row["is_active"]),
        has_api_key=bool(row["api_key_ref"]),
    )


@router.put("/config", response_model=LLMConfigPayload)
async def update_config(payload: LLMConfigPayload) -> LLMConfigPayload:
    """Persist a new LLM configuration. The API key (if provided) goes to the keyring."""
    if payload.api_key is not None:
        if payload.api_key:
            keyring.store(_API_KEY_REF, payload.api_key)
            api_key_ref: str | None = _API_KEY_REF
        else:
            keyring.delete(_API_KEY_REF)
            api_key_ref = None
    else:
        # Preserve existing api_key_ref.
        existing = get_connection().execute("SELECT api_key_ref FROM llm_config WHERE id = 1").fetchone()
        api_key_ref = existing["api_key_ref"] if existing else None

    with transaction() as conn:
        conn.execute(
            """
            UPDATE llm_config SET
                provider = ?, model = ?, max_tokens = ?, temperature = ?,
                monthly_budget_cents = ?, is_active = ?, api_key_ref = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id = 1
            """,
            (
                payload.provider,
                payload.model,
                payload.max_tokens,
                payload.temperature,
                payload.monthly_budget_cents,
                1 if payload.is_active else 0,
                api_key_ref,
            ),
        )
    return await get_config()


@router.get("/usage", response_model=dict[str, Any])
async def get_usage(limit: int = 50) -> dict[str, Any]:
    """Return cost and call-count summaries plus the most recent log rows."""
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="limit must be 1-1000")
    conn = get_connection()
    summary = conn.execute("""
        SELECT COUNT(*) AS calls,
               COALESCE(SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END), 0) AS cache_hits,
               COALESCE(SUM(prompt_tokens), 0) AS prompt_tokens,
               COALESCE(SUM(completion_tokens), 0) AS completion_tokens,
               COALESCE(SUM(cost_cents), 0) AS cost_cents
        FROM llm_usage_log
        """).fetchone()
    rows = conn.execute("SELECT * FROM llm_usage_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    budget = current_budget_state()
    return {
        "summary": {
            "calls": int(summary["calls"]),
            "cache_hits": int(summary["cache_hits"]),
            "prompt_tokens": int(summary["prompt_tokens"]),
            "completion_tokens": int(summary["completion_tokens"]),
            "cost_cents": float(summary["cost_cents"]),
        },
        "budget": {
            "spent_cents": budget.spent_cents,
            "budget_cents": budget.budget_cents,
            "over_budget": budget.over_budget,
        },
        "recent": [dict(row) for row in rows],
    }


@router.post("/test", response_model=dict[str, Any])
async def test_classify(payload: LLMTestRequest) -> dict[str, Any]:
    """Run one synthetic job through the pipeline and return the result.

    Useful from the dashboard's Settings page — verifies the configured
    API key, model, and prompt construction without waiting for a real
    screen change.
    """
    row = (
        get_connection()
        .execute("SELECT provider, model, max_tokens, temperature, api_key_ref " "FROM llm_config WHERE id = 1")
        .fetchone()
    )
    if row is None or not row["api_key_ref"]:
        raise HTTPException(status_code=400, detail="LLM is not configured")
    api_key = keyring.retrieve(str(row["api_key_ref"]))
    if not api_key:
        raise HTTPException(status_code=400, detail="API key missing from keyring")

    factory = ClaudeClient if row["provider"] != "openai" else OpenAIClient
    client = factory(
        api_key,
        model=row["model"],
        max_tokens=int(row["max_tokens"]),
        temperature=float(row["temperature"]),
    )
    context = ClassificationContext(
        process_name=payload.process_name,
        redacted_title=payload.window_title,
        redacted_ocr_text=payload.ocr_text,
    )
    user_prompt = build_user_prompt(context, projects=[], task_categories=["development"])
    try:
        result = client.classify(SYSTEM_PROMPT, user_prompt)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "project": result.project,
        "task": result.task,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "latency_ms": result.latency_ms,
        "raw_json": result.raw_json,
    }


@router.post("/classify", response_model=dict[str, Any])
async def classify_now(payload: LLMTestRequest) -> dict[str, Any]:
    """Run one job through the full pipeline (redact + cache + LLM)."""
    job = ClassificationJob(
        activity_id=0,
        captured_at=datetime.now(tz=UTC),
        window_title=payload.window_title,
        process_name=payload.process_name,
        raw_ocr_text=payload.ocr_text,
        redacted_text=payload.ocr_text,
        phash="",
    )
    pipeline = ClassificationPipeline()
    result = pipeline.process_job(job)
    if result is None:
        return {
            "skipped": True,
            "reason": ("no_api_key" if pipeline.stats.skipped_no_key else "over_budget_or_failure"),
            "stats": dataclasses.asdict(pipeline.stats),
        }
    return {
        "skipped": False,
        "project": result.project,
        "task": result.task,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "stats": dataclasses.asdict(pipeline.stats),
    }
