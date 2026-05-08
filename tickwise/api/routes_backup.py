"""Whole-database export endpoint.

Bundles every user-owned table into a single JSON file the user can
download from Settings. Restoring is intentionally manual — `import`
endpoints are a foot-gun without conflict-resolution UI, so we leave
that to a future release.

We deliberately omit tables that hold derived state (`activities`,
`classification_cache`, `redaction_log`, `llm_usage_log`,
`mobile_auth_tokens`) — they regenerate from new captures and keeping
them out drops the export from megabytes to kilobytes for most users.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response

from tickwise import __version__
from tickwise.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backup", tags=["backup"])

_EXPORTED_TABLES = (
    "projects",
    "clients",
    "task_categories",
    "sessions",
    "pomodoro_sessions",
    "invoices",
    "invoice_line_items",
    "freelancer_profile",
    "calendar_providers",
    "ics_feed_config",
    "cloudflare_config",
    "llm_config",
    "custom_redaction_rules",
    "settings",
    "monitor_preferences",
)


def _dump_table(table: str) -> list[dict[str, Any]]:
    rows = get_connection().execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608 — table from allowlist
    return [dict(r) for r in rows]


@router.get("/export")
async def export_backup() -> Response:
    """Return a JSON document covering every user-owned table."""
    conn = get_connection()
    schema_version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    payload = {
        "exported_at": datetime.now(tz=UTC).isoformat(),
        "app_version": __version__,
        "schema_version": int(schema_version or 0),
        "tables": {table: _dump_table(table) for table in _EXPORTED_TABLES},
    }
    body = json.dumps(payload, indent=2, default=str)
    filename = f"tickwise-backup-{datetime.now(tz=UTC).strftime('%Y%m%d-%H%M%S')}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
