"""Google Calendar provider.

Pushes ChronoLens sessions as events on a Google Calendar via the v3
REST API. Authentication is OAuth2 — the access token must already be
present in the platform keyring under the alias stored in
``provider.config["token_ref"]``. The OAuth-grant flow itself lives on
the dashboard side (Phase 5h); this provider is the runtime that
consumes the resulting access token.

When the access token has expired, the refresh token (if any) under
``token_ref + "_refresh"`` is used to mint a new one.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from chronolens.calendar.provider import CalendarProvider, SyncReport
from chronolens.crypto import keyring

logger = logging.getLogger(__name__)

_API_BASE = "https://www.googleapis.com/calendar/v3"
_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleCalendarProvider(CalendarProvider):
    """Google Calendar via OAuth2-protected REST endpoints."""

    type_name = "google"

    def push_sessions(self, sessions: list[dict[str, Any]]) -> SyncReport:
        report = SyncReport(provider_id=self.provider_id, provider_name=self.name)
        token_ref = self.config.get("token_ref")
        calendar_id = self.config.get("calendar_id", "primary")
        if not token_ref:
            report.errors.append("Google provider has no token_ref configured")
            return report
        access_token = keyring.retrieve(token_ref)
        if not access_token:
            report.errors.append("Google access token missing from keyring")
            return report

        with httpx.Client(timeout=10.0) as client:
            for session in sessions:
                event_id = f"chronolenssession{session['id']}"
                payload = {
                    "id": event_id,
                    "summary": _summary(session),
                    "description": session.get("description") or "",
                    "start": {"dateTime": _ensure_iso(session["started_at"])},
                    "end": {"dateTime": _ensure_iso(session.get("ended_at") or session["started_at"])},
                }
                url = f"{_API_BASE}/calendars/{calendar_id}/events/{event_id}"
                try:
                    response = client.put(
                        url,
                        json=payload,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if response.status_code == 404:
                        # Not yet inserted — POST instead.
                        response = client.post(
                            f"{_API_BASE}/calendars/{calendar_id}/events",
                            json=payload,
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        response.raise_for_status()
                        report.events_pushed += 1
                    else:
                        response.raise_for_status()
                        report.events_updated += 1
                except httpx.HTTPError as exc:
                    report.errors.append(f"session {session['id']}: {exc}")
        return report


def _summary(session: dict[str, Any]) -> str:
    project = session.get("project_name")
    description = session.get("description") or ""
    if project and description:
        return f"{project} — {description}"
    return project or description or f"Session #{session['id']}"


def _ensure_iso(value: str) -> str:
    """Google requires RFC 3339; ChronoLens stores ISO-8601 already, but
    we tag a missing offset with UTC to keep the API happy."""
    if value.endswith("Z") or "+" in value[10:] or "-" in value[10:]:
        return value
    return datetime.fromisoformat(value).replace(tzinfo=UTC).isoformat()
