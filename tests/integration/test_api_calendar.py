"""Integration tests for /api/calendar endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tickwise.db.connection import transaction


def _seed_session(started: str = "2026-05-08T09:00:00", duration: int = 600) -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (started_at, ended_at, duration_secs) VALUES (?, ?, ?)",
            (started, "2026-05-08T09:10:00", duration),
        )
        return int(cur.lastrowid or 0)


@pytest.mark.integration
class TestFeedCRUD:
    def test_create_list_delete(self, client: TestClient) -> None:
        r = client.post("/api/calendar/feeds", json={"name": "Tuta", "include_descriptions": True})
        assert r.status_code == 201
        body = r.json()
        assert len(body["token"]) == 32

        listed = client.get("/api/calendar/feeds").json()
        assert any(f["id"] == body["id"] for f in listed)

        assert client.delete(f"/api/calendar/feeds/{body['id']}").status_code == 204
        assert client.delete(f"/api/calendar/feeds/{body['id']}").status_code == 404

    def test_serve_feed(self, client: TestClient) -> None:
        _seed_session()
        feed = client.post("/api/calendar/feeds", json={"name": "Tuta"}).json()
        r = client.get(f"/api/calendar/feed/{feed['token']}.ics")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/calendar")
        body = r.text
        assert "BEGIN:VCALENDAR" in body
        assert "END:VCALENDAR" in body

    def test_unknown_token_404(self, client: TestClient) -> None:
        r = client.get("/api/calendar/feed/deadbeef.ics")
        assert r.status_code == 404

    def test_inactive_feed_404(self, client: TestClient) -> None:
        feed = client.post("/api/calendar/feeds", json={"name": "Off", "is_active": False}).json()
        r = client.get(f"/api/calendar/feed/{feed['token']}.ics")
        assert r.status_code == 404


@pytest.mark.integration
class TestExport:
    def test_export_returns_attachment(self, client: TestClient) -> None:
        _seed_session()
        r = client.get("/api/calendar/export.ics")
        assert r.status_code == 200
        assert "attachment" in r.headers["content-disposition"]
        assert "BEGIN:VCALENDAR" in r.text


@pytest.mark.integration
class TestProviderCRUD:
    def test_create_list_delete(self, client: TestClient) -> None:
        r = client.post(
            "/api/calendar/providers",
            json={"name": "MyDAV", "type": "caldav", "url": "https://"},
        )
        assert r.status_code == 201
        pid = r.json()["id"]
        listed = client.get("/api/calendar/providers").json()
        assert any(p["id"] == pid for p in listed)
        assert client.delete(f"/api/calendar/providers/{pid}").status_code == 204
        assert client.delete(f"/api/calendar/providers/{pid}").status_code == 404


@pytest.mark.integration
class TestSync:
    def test_sync_returns_per_provider_reports(self, client: TestClient) -> None:
        # No active providers — empty list, but endpoint succeeds.
        r = client.post("/api/calendar/sync", json={})
        assert r.status_code == 200
        assert r.json() == []
