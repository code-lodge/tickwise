"""Integration tests for the bearer-authenticated /api/mobile/* endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tickwise.db.connection import transaction


def _seed_session_today(project_name: str = "Acme", duration: int = 3600) -> None:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, hourly_rate, currency) VALUES (?, ?, ?)",
            (project_name, 75.0, "EUR"),
        )
        project_id = int(cur.lastrowid or 0)
        conn.execute(
            "INSERT INTO sessions (started_at, ended_at, duration_secs, project_id) "
            "VALUES (datetime('now'), datetime('now', '+1 hour'), ?, ?)",
            (duration, project_id),
        )


def _pair(client: TestClient, name: str = "Phone") -> str:
    r = client.post("/api/pairing/start", json={"device_name": name})
    assert r.status_code == 200
    return str(r.json()["token"])


@pytest.mark.integration
class TestPairing:
    def test_start_pairing_emits_qr(self, client: TestClient) -> None:
        r = client.post("/api/pairing/start", json={"device_name": "iPhone 15"})
        assert r.status_code == 200
        body = r.json()
        assert body["token"]
        assert "<svg" in body["qr_svg"]
        assert body["pairing_url"].endswith(f"?t={body['token']}")

    def test_list_then_revoke(self, client: TestClient) -> None:
        token = _pair(client, "to-revoke")
        r = client.get("/api/pairing/tokens")
        assert any(d["device_name"] == "to-revoke" for d in r.json())
        token_id = next(d["id"] for d in r.json() if d["device_name"] == "to-revoke")
        assert client.delete(f"/api/pairing/tokens/{token_id}").status_code == 204
        # Subsequent authenticated calls should fail.
        assert client.get("/api/mobile/whoami", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    def test_revoke_unknown_returns_404(self, client: TestClient) -> None:
        assert client.delete("/api/pairing/tokens/9999").status_code == 404


@pytest.mark.integration
class TestMobileAuth:
    def test_unauthenticated_rejected(self, client: TestClient) -> None:
        for path in ["/api/mobile/whoami", "/api/mobile/today", "/api/mobile/timeline"]:
            assert client.get(path).status_code == 401

    def test_whoami_after_pairing(self, client: TestClient) -> None:
        token = _pair(client, "iPad")
        r = client.get("/api/mobile/whoami", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["device_name"] == "iPad"


@pytest.mark.integration
class TestMobileEndpoints:
    def test_today_aggregates_by_project(self, client: TestClient) -> None:
        _seed_session_today("Alpha", 1800)
        _seed_session_today("Alpha", 600)
        _seed_session_today("Beta", 900)
        token = _pair(client)
        r = client.get("/api/mobile/today", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["session_count"] == 3
        names = sorted(p["name"] for p in body["by_project"])
        assert names == ["Alpha", "Beta"]

    def test_timeline_lists_recent_sessions(self, client: TestClient) -> None:
        _seed_session_today("Alpha", 1800)
        token = _pair(client)
        r = client.get(
            "/api/mobile/timeline?days=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert rows[0]["project_name"] == "Alpha"

    def test_pomodoro_start_via_mobile(self, client: TestClient) -> None:
        from tickwise import runtime

        runtime.set_pomodoro_timer(None)
        token = _pair(client)
        r = client.post(
            "/api/mobile/pomodoro/start?target=focus",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["state"] == "focus"

    def test_pomodoro_invalid_target(self, client: TestClient) -> None:
        from tickwise import runtime

        runtime.set_pomodoro_timer(None)
        token = _pair(client)
        r = client.post(
            "/api/mobile/pomodoro/start?target=weird",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422

    def test_projects_only_active(self, client: TestClient) -> None:
        with transaction() as conn:
            conn.execute("INSERT INTO projects (name, is_active) VALUES (?, 1)", ("Live",))
            conn.execute("INSERT INTO projects (name, is_active) VALUES (?, 0)", ("Archived",))
        token = _pair(client)
        r = client.get("/api/mobile/projects", headers={"Authorization": f"Bearer {token}"})
        names = [p["name"] for p in r.json()]
        assert "Live" in names
        assert "Archived" not in names
