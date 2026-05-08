"""First-run / onboarding state.

The dashboard hits this on every boot to decide whether to drop the user
into the setup wizard. The server is the source of truth — the dashboard
is otherwise stateless about onboarding so a freshly-installed device
sees the wizard even if it's reusing a browser profile from another box.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from tickwise.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/state")
async def state() -> dict[str, Any]:
    """Return what's missing for a complete first-run setup.

    Each ``needs_*`` flag mirrors a wizard step in the dashboard.
    Falsy/empty checks instead of truthy presence so a user who deletes
    their only project gets nudged back into the wizard, not stuck on a
    blank page.
    """
    conn = get_connection()
    profile = conn.execute("SELECT name, email FROM freelancer_profile WHERE id = 1").fetchone()
    has_profile = bool(profile and (profile["name"] or "").strip())

    project_count = int(conn.execute("SELECT COUNT(*) FROM projects WHERE is_active = 1").fetchone()[0])
    privacy_level = conn.execute("SELECT value FROM settings WHERE key = 'privacy_level'").fetchone()
    has_privacy = privacy_level is not None

    needs = {
        "needs_profile": not has_profile,
        "needs_first_project": project_count == 0,
        "needs_privacy_choice": not has_privacy,
    }
    return {
        **needs,
        "is_first_run": all(needs.values()),
        "complete": not any(needs.values()),
    }
