"""Unit tests for the calendar sync service + provider dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tickwise.calendar.provider import CalendarProvider, SyncReport
from tickwise.calendar.sync_service import (
    CalendarSyncService,
    build_provider_for_row,
)
from tickwise.db.connection import get_connection, transaction


def _seed_session(started: datetime, duration: int = 600) -> int:
    ended = started + timedelta(seconds=duration)
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (started_at, ended_at, duration_secs) VALUES (?, ?, ?)",
            (started.isoformat(), ended.isoformat(), duration),
        )
        return int(cur.lastrowid or 0)


def _add_provider(name: str, ptype: str, url: str = "x") -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO calendar_providers (name, type, url, is_active) VALUES (?, ?, ?, 1)",
            (name, ptype, url),
        )
        return int(cur.lastrowid or 0)


@pytest.mark.unit
class TestSyncService:
    def test_pushes_sessions_to_active_providers(self, tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _seed_session(datetime.now(tz=UTC) - timedelta(hours=1))
        provider_id = _add_provider("My CalDAV", "caldav")

        captured: list[list[dict]] = []

        class FakeProvider(CalendarProvider):
            type_name = "caldav"

            def push_sessions(self, sessions: list[dict]) -> SyncReport:
                captured.append(sessions)
                return SyncReport(
                    provider_id=self.provider_id,
                    provider_name=self.name,
                    events_pushed=len(sessions),
                )

        from tickwise.calendar import sync_service as svc

        monkeypatch.setattr(
            svc,
            "build_provider_for_row",
            lambda row: FakeProvider(int(row["id"]), str(row["name"]), {}),
        )

        reports = CalendarSyncService(lookback_days=2).run_once()
        assert len(reports) == 1
        assert reports[0].events_pushed == 1
        assert captured and len(captured[0]) == 1

        # Sync log row written.
        rows = get_connection().execute("SELECT * FROM sync_log WHERE provider_id = ?", (provider_id,)).fetchall()
        assert len(rows) == 1
        assert rows[0]["events_exported"] == 1

        # `last_synced_at` updated on the provider row.
        provider = (
            get_connection()
            .execute("SELECT last_synced_at FROM calendar_providers WHERE id = ?", (provider_id,))
            .fetchone()
        )
        assert provider["last_synced_at"] is not None

    def test_provider_crash_does_not_propagate(self, tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _seed_session(datetime.now(tz=UTC))
        _add_provider("Crashes", "caldav")

        class Boom(CalendarProvider):
            type_name = "caldav"

            def push_sessions(self, sessions: list[dict]) -> SyncReport:
                raise RuntimeError("something bad")

        from tickwise.calendar import sync_service as svc

        monkeypatch.setattr(
            svc,
            "build_provider_for_row",
            lambda row: Boom(int(row["id"]), str(row["name"]), {}),
        )

        reports = CalendarSyncService().run_once()
        assert len(reports) == 1
        assert "something bad" in reports[0].errors[0]

    def test_skips_providers_when_inactive(self, tmp_db: Path) -> None:
        # An inactive provider isn't iterated.
        _add_provider("Quiet", "caldav")
        with transaction() as conn:
            conn.execute("UPDATE calendar_providers SET is_active = 0")
        reports = CalendarSyncService().run_once()
        assert reports == []


@pytest.mark.unit
class TestBuildProvider:
    def test_caldav_resolves(self) -> None:
        provider = build_provider_for_row({"id": 1, "name": "x", "type": "caldav", "url": "https://", "username": None})
        assert provider is not None
        assert provider.type_name == "caldav"

    def test_google_resolves(self) -> None:
        provider = build_provider_for_row({"id": 1, "name": "x", "type": "google", "url": "primary", "username": None})
        assert provider is not None
        assert provider.type_name == "google"

    def test_ical_returns_none(self) -> None:
        provider = build_provider_for_row({"id": 1, "name": "x", "type": "ical", "url": "u", "username": None})
        assert provider is None

    def test_unknown_returns_none(self) -> None:
        provider = build_provider_for_row({"id": 1, "name": "x", "type": "imap", "url": "u", "username": None})
        assert provider is None


@pytest.mark.unit
class TestCalDAVProvider:
    def test_missing_caldav_library_records_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Force the lazy import to fail.
        import builtins

        from tickwise.calendar.caldav_provider import CalDAVProvider

        real_import = builtins.__import__

        def _raise(name: str, *a: object, **kw: object) -> object:
            if name == "caldav":
                raise ImportError("not installed")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", _raise)
        provider = CalDAVProvider(1, "x", {"url": "https://"})
        report = provider.push_sessions([{"id": 1}])
        assert report.errors == ["caldav library not installed"]

    def test_missing_url_records_error(self) -> None:
        from tickwise.calendar.caldav_provider import CalDAVProvider

        provider = CalDAVProvider(1, "x", {})
        report = provider.push_sessions([{"id": 1}])
        # One of the two error messages will be present, depending on which
        # check fires first when the caldav library isn't installed.
        assert report.errors

    def test_no_sessions_returns_empty_report(self) -> None:
        from tickwise.calendar.caldav_provider import CalDAVProvider

        provider = CalDAVProvider(1, "x", {"url": "https://"})
        report = provider.push_sessions([])
        assert report.events_pushed == 0
        assert report.events_updated == 0
        assert report.errors == []


@pytest.mark.unit
class TestGoogleProvider:
    def test_missing_token_ref(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from tickwise.calendar.google_provider import GoogleCalendarProvider
        from tickwise.crypto import keyring

        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()

        provider = GoogleCalendarProvider(1, "x", {})
        report = provider.push_sessions([{"id": 1}])
        assert "no token_ref" in report.errors[0]

    def test_missing_token_in_keyring(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        from tickwise.calendar.google_provider import GoogleCalendarProvider
        from tickwise.crypto import keyring

        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()

        provider = GoogleCalendarProvider(1, "x", {"token_ref": "google_1"})
        report = provider.push_sessions([{"id": 1}])
        assert "access token missing" in report.errors[0]

    def test_request_uses_bearer(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        import httpx

        from tickwise.calendar.google_provider import GoogleCalendarProvider
        from tickwise.crypto import keyring

        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()
        keyring.store("google_1", "tok-secret")

        observed: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            observed["auth"] = request.headers.get("Authorization", "")
            observed["method"] = request.method
            return httpx.Response(200, json={"id": "ok"})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        # Patch the module's httpx.Client to return our mocked one.
        import tickwise.calendar.google_provider as mod

        class _CM:
            def __enter__(self) -> httpx.Client:
                return client

            def __exit__(self, *_: object) -> None:
                return None

        monkeypatch.setattr(mod.httpx, "Client", lambda **_kw: _CM())
        provider = GoogleCalendarProvider(1, "x", {"token_ref": "google_1"})
        report = provider.push_sessions(
            [
                {
                    "id": 7,
                    "started_at": "2026-05-08T09:00:00+00:00",
                    "ended_at": "2026-05-08T10:00:00+00:00",
                    "description": None,
                    "project_name": None,
                }
            ]
        )
        assert observed["auth"] == "Bearer tok-secret"
        assert report.events_updated == 1
