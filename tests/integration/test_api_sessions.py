"""Integration tests for /api/sessions endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from chronolens.db.connection import transaction


def _insert_session(started_at: datetime, duration: int = 60, description: str = "test") -> int:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO sessions (started_at, ended_at, duration_secs, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                started_at.isoformat(),
                (started_at + timedelta(seconds=duration)).isoformat(),
                duration,
                description,
            ),
        )
        return int(cur.lastrowid or 0)


@pytest.mark.integration
class TestListSessions:
    def test_empty(self, client: TestClient) -> None:
        r = client.get("/api/sessions")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_inserted(self, client: TestClient) -> None:
        sid = _insert_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        r = client.get("/api/sessions")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["id"] == sid
        assert body[0]["duration_secs"] == 60

    def test_filters_by_from_to(self, client: TestClient) -> None:
        _insert_session(datetime(2026, 5, 1, 9, 0, tzinfo=UTC), description="old")
        _insert_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), description="new")
        r = client.get("/api/sessions?from=2026-05-05T00:00:00+00:00")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["description"] == "new"

    def test_orders_desc(self, client: TestClient) -> None:
        _insert_session(datetime(2026, 5, 1, 9, 0, tzinfo=UTC), description="a")
        _insert_session(datetime(2026, 5, 2, 9, 0, tzinfo=UTC), description="b")
        body = client.get("/api/sessions").json()
        assert [r["description"] for r in body] == ["b", "a"]


@pytest.mark.integration
class TestGetSession:
    def test_found(self, client: TestClient) -> None:
        sid = _insert_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        r = client.get(f"/api/sessions/{sid}")
        assert r.status_code == 200
        assert r.json()["id"] == sid

    def test_not_found(self, client: TestClient) -> None:
        r = client.get("/api/sessions/9999")
        assert r.status_code == 404
