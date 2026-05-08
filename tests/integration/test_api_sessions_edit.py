"""Integration tests for the new session edit / split / merge endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from chronolens.db.connection import transaction


def _seed_session(started: datetime, duration_secs: int = 600, **extra) -> int:
    ended = started + timedelta(seconds=duration_secs)
    cols = ["started_at", "ended_at", "duration_secs"]
    vals: list = [started.isoformat(), ended.isoformat(), duration_secs]
    for k, v in extra.items():
        cols.append(k)
        vals.append(v)
    placeholders = ", ".join("?" * len(cols))
    with transaction() as conn:
        cur = conn.execute(f"INSERT INTO sessions ({', '.join(cols)}) VALUES ({placeholders})", vals)
        return int(cur.lastrowid or 0)


@pytest.mark.integration
class TestUpdateSession:
    def test_patch_project_and_description(self, client: TestClient) -> None:
        sid = _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
        r = client.put(
            f"/api/sessions/{sid}",
            json={"project_id": pid, "description": "Investigation work"},
        )
        assert r.status_code == 200
        assert r.json()["project_id"] == pid
        assert r.json()["description"] == "Investigation work"

    def test_empty_payload_is_422(self, client: TestClient) -> None:
        sid = _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        assert client.put(f"/api/sessions/{sid}", json={}).status_code == 422

    def test_missing_session_returns_404(self, client: TestClient) -> None:
        assert client.put("/api/sessions/9999", json={"description": "x"}).status_code == 404


@pytest.mark.integration
class TestSplitSession:
    def test_splits_into_two(self, client: TestClient) -> None:
        start = datetime(2026, 5, 8, 9, 0, tzinfo=UTC)
        sid = _seed_session(start, duration_secs=600)
        split_at = (start + timedelta(seconds=200)).isoformat()
        r = client.post(f"/api/sessions/{sid}/split", json={"split_at": split_at})
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 2
        assert rows[0]["duration_secs"] == 200
        assert rows[1]["duration_secs"] == 400

    def test_split_outside_range_rejected(self, client: TestClient) -> None:
        start = datetime(2026, 5, 8, 9, 0, tzinfo=UTC)
        sid = _seed_session(start, duration_secs=600)
        outside = (start - timedelta(seconds=5)).isoformat()
        r = client.post(f"/api/sessions/{sid}/split", json={"split_at": outside})
        assert r.status_code == 422

    def test_invalid_iso_rejected(self, client: TestClient) -> None:
        sid = _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        r = client.post(f"/api/sessions/{sid}/split", json={"split_at": "bogus"})
        assert r.status_code == 422

    def test_missing_session(self, client: TestClient) -> None:
        r = client.post("/api/sessions/9999/split", json={"split_at": "2026-05-08T09:00:00"})
        assert r.status_code == 404


@pytest.mark.integration
class TestMergeSessions:
    def test_merge_combines_durations(self, client: TestClient) -> None:
        a = _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), duration_secs=300)
        b = _seed_session(datetime(2026, 5, 8, 10, 0, tzinfo=UTC), duration_secs=400)
        r = client.post(f"/api/sessions/{a}/merge", json={"other_id": b})
        assert r.status_code == 200
        body = r.json()
        assert body["duration_secs"] == 700
        # Source row removed.
        assert client.get(f"/api/sessions/{b}").status_code == 404

    def test_self_merge_rejected(self, client: TestClient) -> None:
        sid = _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        r = client.post(f"/api/sessions/{sid}/merge", json={"other_id": sid})
        assert r.status_code == 422

    def test_missing_partner(self, client: TestClient) -> None:
        sid = _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        r = client.post(f"/api/sessions/{sid}/merge", json={"other_id": 9999})
        assert r.status_code == 404


@pytest.mark.integration
class TestDeleteSession:
    def test_delete(self, client: TestClient) -> None:
        sid = _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC))
        assert client.delete(f"/api/sessions/{sid}").status_code == 204
        assert client.get(f"/api/sessions/{sid}").status_code == 404

    def test_delete_missing(self, client: TestClient) -> None:
        assert client.delete("/api/sessions/9999").status_code == 404


@pytest.mark.integration
class TestTodaySummary:
    def test_zero_when_empty(self, client: TestClient) -> None:
        body = client.get("/api/sessions/summary/today").json()
        assert body["total_seconds"] == 0
        assert body["session_count"] == 0
        assert body["by_project"] == []

    def test_aggregates_today(self, client: TestClient) -> None:
        # Seed sessions for "today" (UTC) so the summary picks them up.
        today = datetime.now(tz=UTC).replace(hour=9, minute=0, second=0, microsecond=0)
        _seed_session(today, duration_secs=600, is_billed=1)
        _seed_session(today + timedelta(hours=1), duration_secs=300)
        body = client.get("/api/sessions/summary/today").json()
        assert body["total_seconds"] >= 900
        assert body["billable_seconds"] >= 600
