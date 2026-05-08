"""CalDAV (RFC 4791) sync provider.

Uses the `caldav` Python library when installed. ChronoLens identifies
each event by its session id via the iCalendar `UID` so re-running sync
is idempotent — existing events are updated in place rather than
duplicated.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from chronolens.calendar.ics_feed import build_calendar
from chronolens.calendar.provider import CalendarProvider, SyncReport

logger = logging.getLogger(__name__)


class CalDAVProvider(CalendarProvider):
    """Push sessions to a CalDAV server (Radicale, Nextcloud, Apple, …)."""

    type_name = "caldav"

    def push_sessions(self, sessions: list[dict[str, Any]]) -> SyncReport:
        report = SyncReport(provider_id=self.provider_id, provider_name=self.name)
        if not sessions:
            return report
        try:
            import caldav
        except ImportError:
            report.errors.append("caldav library not installed")
            return report

        url = self.config.get("url")
        username = self.config.get("username")
        password = self.config.get("password")
        if not url:
            report.errors.append("CalDAV provider missing URL")
            return report

        try:
            client = caldav.DAVClient(url=url, username=username, password=password)
            principal = client.principal()
            calendars = principal.calendars()
            if not calendars:
                report.errors.append("no CalDAV calendars on server")
                return client_close(client, report)
            target = calendars[0]
        except Exception as exc:  # noqa: BLE001 — sync should not crash
            report.errors.append(f"CalDAV connection failed: {exc}")
            return report

        try:
            existing = {event.icalendar_component.get("UID"): event for event in target.events()}
        except Exception:  # noqa: BLE001
            existing = {}
            logger.exception("CalDAV listing failed for %s", self.name)

        for session in sessions:
            uid = f"chronolens-session-{session['id']}@chronolens"
            ics = build_calendar([session])
            try:
                if uid in existing:
                    existing[uid].data = ics
                    existing[uid].save()
                    report.events_updated += 1
                else:
                    target.add_event(ics)
                    report.events_pushed += 1
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"session {session['id']}: {exc}")
        return client_close(client, report)


def client_close(client: Any, report: SyncReport) -> SyncReport:
    """Best-effort close on the underlying transport."""
    close = getattr(client, "close", None)
    if callable(close):
        with contextlib.suppress(Exception):
            close()
    return report
