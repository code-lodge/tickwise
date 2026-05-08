"""Calendar sync orchestration.

Loads active provider rows, instantiates the right :class:`CalendarProvider`
subclass, and pushes recent sessions to each. Results land in the
``sync_log`` table for the dashboard to surface; a single API call can
trigger an immediate sync, while the background scheduler runs them on
an interval.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from chronolens.calendar.caldav_provider import CalDAVProvider
from chronolens.calendar.google_provider import GoogleCalendarProvider
from chronolens.calendar.provider import CalendarProvider, SyncReport
from chronolens.crypto import keyring
from chronolens.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

_DEFAULT_LOOKBACK_DAYS = 7


@dataclass(slots=True)
class CalendarSyncService:
    """Coordinates one sync run across all active calendar providers."""

    lookback_days: int = _DEFAULT_LOOKBACK_DAYS

    def run_once(self) -> list[SyncReport]:
        """Execute a single end-to-end sync. Returns one report per provider."""
        sessions = list(self._fetch_recent_sessions())
        reports: list[SyncReport] = []
        for provider in self._iter_active_providers():
            try:
                report = provider.push_sessions(sessions)
            except Exception as exc:  # noqa: BLE001 — never let one provider kill the loop
                report = SyncReport(
                    provider_id=provider.provider_id,
                    provider_name=provider.name,
                    errors=[f"unexpected: {exc}"],
                )
                logger.exception("Sync crashed for provider %s", provider.name)
            self._record(report)
            reports.append(report)
        return reports

    # ─── helpers ─────────────────────────────────────────────────────────

    def _fetch_recent_sessions(self) -> Iterable[dict[str, Any]]:
        cutoff = (datetime.now(tz=UTC) - timedelta(days=self.lookback_days)).isoformat()
        rows = (
            get_connection()
            .execute(
                """
                SELECT s.id, s.started_at, s.ended_at, s.duration_secs, s.description,
                       p.name AS project_name, p.color AS project_color
                  FROM sessions s
                  LEFT JOIN projects p ON p.id = s.project_id
                 WHERE s.started_at >= ?
                   AND s.duration_secs IS NOT NULL
                 ORDER BY s.started_at
                """,
                (cutoff,),
            )
            .fetchall()
        )
        return [dict(row) for row in rows]

    def _iter_active_providers(self) -> Iterable[CalendarProvider]:
        rows = (
            get_connection()
            .execute("SELECT id, name, type, url, username FROM calendar_providers " "WHERE is_active = 1 ORDER BY id")
            .fetchall()
        )
        for row in rows:
            provider = build_provider_for_row(dict(row))
            if provider is not None:
                yield provider

    def _record(self, report: SyncReport) -> None:
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO sync_log
                    (provider_id, events_imported, events_exported, error)
                VALUES (?, ?, ?, ?)
                """,
                (
                    report.provider_id,
                    0,
                    report.events_pushed + report.events_updated,
                    json.dumps(report.errors) if report.errors else None,
                ),
            )
            conn.execute(
                "UPDATE calendar_providers SET last_synced_at = ?, "
                "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                (datetime.now(tz=UTC).isoformat(), report.provider_id),
            )


def build_provider_for_row(row: dict[str, Any]) -> CalendarProvider | None:
    """Translate a `calendar_providers` row into a runtime provider."""
    provider_type = row.get("type")
    config: dict[str, Any] = {
        "url": row.get("url"),
        "username": row.get("username"),
    }
    if row.get("username"):
        secret = keyring.retrieve(f"caldav_{row['id']}")
        if secret:
            config["password"] = secret
    if provider_type == "caldav":
        return CalDAVProvider(int(row["id"]), str(row["name"]), config)
    if provider_type == "google":
        config["token_ref"] = f"google_{row['id']}"
        config["calendar_id"] = row.get("url") or "primary"
        return GoogleCalendarProvider(int(row["id"]), str(row["name"]), config)
    if provider_type == "ical":
        return None  # ICS feeds are pull-based; nothing to push.
    logger.warning("Unknown calendar provider type: %s", provider_type)
    return None
