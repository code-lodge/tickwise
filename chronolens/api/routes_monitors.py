"""Multi-monitor configuration endpoints.

Surfaces the detected monitors (live, via mss) and the user's per-monitor
capture preferences (persisted in `monitor_preferences`). The capture
loop reads the preferences each tick to decide which displays to grab.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from chronolens.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


class MonitorEntry(BaseModel):
    index: int
    left: int
    top: int
    width: int
    height: int
    label: str | None = None
    enabled: bool = True
    is_primary: bool = False


class MonitorPreference(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    enabled: bool = True
    is_primary: bool = False


def _detect_monitors() -> list[dict[str, Any]]:
    """Probe mss for the connected displays. Empty list when mss is unusable."""
    try:
        from chronolens.capture.screenshot import ScreenCapturer

        with ScreenCapturer() as cap:
            return [
                {
                    "index": m.index,
                    "left": m.left,
                    "top": m.top,
                    "width": m.width,
                    "height": m.height,
                }
                for m in cap.list_monitors()
            ]
    except Exception:
        logger.exception("monitor detection failed")
        return []


def _load_prefs() -> dict[int, dict[str, Any]]:
    rows = (
        get_connection().execute("SELECT monitor_index, label, enabled, is_primary FROM monitor_preferences").fetchall()
    )
    return {
        int(r["monitor_index"]): {
            "label": r["label"],
            "enabled": bool(r["enabled"]),
            "is_primary": bool(r["is_primary"]),
        }
        for r in rows
    }


@router.get("", response_model=list[MonitorEntry])
async def list_monitors() -> list[MonitorEntry]:
    detected = _detect_monitors()
    prefs = _load_prefs()
    out: list[MonitorEntry] = []
    for m in detected:
        pref = prefs.get(m["index"], {})
        out.append(
            MonitorEntry(
                index=m["index"],
                left=m["left"],
                top=m["top"],
                width=m["width"],
                height=m["height"],
                label=pref.get("label"),
                enabled=pref.get("enabled", True),
                is_primary=pref.get("is_primary", m["index"] == 1),
            )
        )
    return out


@router.put("/{index}", response_model=MonitorEntry)
async def update_monitor(index: int, payload: MonitorPreference) -> MonitorEntry:
    if index < 1:
        raise HTTPException(status_code=422, detail="monitor index must be >= 1")
    with transaction() as conn:
        if payload.is_primary:
            # Only one primary at a time.
            conn.execute("UPDATE monitor_preferences SET is_primary = 0")
        conn.execute(
            """
            INSERT INTO monitor_preferences (monitor_index, label, enabled, is_primary)
                 VALUES (?, ?, ?, ?)
            ON CONFLICT(monitor_index) DO UPDATE SET
                 label = excluded.label,
                 enabled = excluded.enabled,
                 is_primary = excluded.is_primary,
                 updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            """,
            (index, payload.label, int(payload.enabled), int(payload.is_primary)),
        )
    detected = next((m for m in _detect_monitors() if m["index"] == index), None)
    if detected is None:
        # Allow saving prefs for a monitor that's currently disconnected — return
        # a synthetic entry so the dashboard can still render the row.
        return MonitorEntry(
            index=index,
            left=0,
            top=0,
            width=0,
            height=0,
            label=payload.label,
            enabled=payload.enabled,
            is_primary=payload.is_primary,
        )
    return MonitorEntry(
        index=detected["index"],
        left=detected["left"],
        top=detected["top"],
        width=detected["width"],
        height=detected["height"],
        label=payload.label,
        enabled=payload.enabled,
        is_primary=payload.is_primary,
    )
