"""Integration tests for /api/pomodoro endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chronolens import runtime


@pytest.fixture(autouse=True)
def _reset_timer() -> None:
    runtime.set_pomodoro_timer(None)


@pytest.mark.integration
class TestStatusAndSettings:
    def test_default_status_is_idle(self, client: TestClient) -> None:
        r = client.get("/api/pomodoro/status")
        assert r.status_code == 200
        body = r.json()
        assert body["state"] == "idle"
        assert body["remaining_secs"] == 0

    def test_settings_round_trip(self, client: TestClient) -> None:
        r = client.put(
            "/api/pomodoro/settings",
            json={
                "work_minutes": 30,
                "short_break_minutes": 6,
                "long_break_minutes": 20,
                "cycles_before_long": 3,
                "auto_start": True,
            },
        )
        assert r.status_code == 200

        r = client.get("/api/pomodoro/settings")
        assert r.status_code == 200
        assert r.json()["work_minutes"] == 30
        assert r.json()["auto_start"] is True


@pytest.mark.integration
class TestLifecycle:
    def test_start_focus_then_stop(self, client: TestClient) -> None:
        r = client.post("/api/pomodoro/start", params={"target": "focus"})
        assert r.status_code == 200
        body = r.json()
        assert body["state"] == "focus"
        assert body["current_session_id"] is not None

        r = client.post("/api/pomodoro/stop")
        assert r.status_code == 200
        assert r.json()["state"] == "idle"

    def test_invalid_target_rejected(self, client: TestClient) -> None:
        r = client.post("/api/pomodoro/start", params={"target": "weird"})
        assert r.status_code == 422

    def test_history_lists_sessions(self, client: TestClient) -> None:
        client.post("/api/pomodoro/start", params={"target": "focus"})
        client.post("/api/pomodoro/stop")
        r = client.get("/api/pomodoro/history")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert rows[0]["type"] == "work"

    def test_history_filter_by_type(self, client: TestClient) -> None:
        client.post("/api/pomodoro/start", params={"target": "focus"})
        client.post("/api/pomodoro/stop")
        client.post("/api/pomodoro/start", params={"target": "short_break"})
        client.post("/api/pomodoro/stop")
        r = client.get("/api/pomodoro/history", params={"type": "short_break"})
        assert r.status_code == 200
        rows = r.json()
        assert all(row["type"] == "short_break" for row in rows)
