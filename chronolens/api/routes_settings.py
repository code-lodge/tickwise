"""Settings CRUD endpoints: GET/PUT /api/settings."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chronolens.config import DEFAULTS
from chronolens.db.connection import transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _all_settings() -> dict[str, str]:
    with transaction() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def _get_one(key: str) -> str | None:
    with transaction() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else None


def _set_one(key: str, value: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ', 'now')",
            (key, value),
        )


class SettingValue(BaseModel):
    value: Any


@router.get("", response_model=dict[str, str])
async def get_all_settings() -> dict[str, str]:
    """Return all settings as a flat key→value map."""
    return _all_settings()


@router.put("", response_model=dict[str, str])
async def update_settings(payload: dict[str, Any]) -> dict[str, str]:
    """Bulk-update settings. Only known keys are accepted."""
    unknown = [k for k in payload if k not in DEFAULTS]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown setting keys: {unknown}")
    for key, value in payload.items():
        _set_one(key, str(value).lower() if isinstance(value, bool) else str(value))
    return _all_settings()


@router.get("/{key}", response_model=SettingValue)
async def get_setting(key: str) -> SettingValue:
    """Return the value for a single setting key."""
    value = _get_one(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return SettingValue(value=value)


@router.put("/{key}", response_model=SettingValue)
async def update_setting(key: str, body: SettingValue) -> SettingValue:
    """Update a single setting by key."""
    if key not in DEFAULTS:
        raise HTTPException(status_code=422, detail=f"Unknown setting key: '{key}'")
    raw = body.value
    str_val = str(raw).lower() if isinstance(raw, bool) else str(raw)
    _set_one(key, str_val)
    return SettingValue(value=str_val)
