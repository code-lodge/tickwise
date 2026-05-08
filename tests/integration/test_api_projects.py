"""Integration tests for /api/projects, /api/clients, /api/categories."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chronolens.db.connection import transaction


@pytest.mark.integration
class TestProjects:
    def test_create_list_get(self, client: TestClient) -> None:
        r = client.post(
            "/api/projects",
            json={"name": "Alpha", "color": "#FF0000", "hourly_rate": 90.0},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Alpha"
        assert body["total_seconds"] == 0

        # List
        all_projects = client.get("/api/projects").json()
        assert any(p["id"] == body["id"] for p in all_projects)

        # Get by id
        single = client.get(f"/api/projects/{body['id']}").json()
        assert single["color"] == "#FF0000"

    def test_total_seconds_aggregates(self, client: TestClient) -> None:
        r = client.post("/api/projects", json={"name": "Beta"})
        pid = r.json()["id"]
        with transaction() as conn:
            conn.execute(
                "INSERT INTO sessions (started_at, duration_secs, project_id) " "VALUES (?, ?, ?), (?, ?, ?)",
                ("2026-05-08T09:00:00", 600, pid, "2026-05-08T10:00:00", 1200, pid),
            )
        body = client.get(f"/api/projects/{pid}").json()
        assert body["total_seconds"] == 1800

    def test_update(self, client: TestClient) -> None:
        pid = client.post("/api/projects", json={"name": "Old"}).json()["id"]
        r = client.put(
            f"/api/projects/{pid}",
            json={"name": "New", "color": "#00FF00", "is_active": True},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "New"
        assert r.json()["color"] == "#00FF00"

    def test_soft_delete_marks_inactive(self, client: TestClient) -> None:
        pid = client.post("/api/projects", json={"name": "Gone"}).json()["id"]
        client.delete(f"/api/projects/{pid}")
        body = client.get(f"/api/projects/{pid}").json()
        assert body["is_active"] is False

    def test_active_only_filter(self, client: TestClient) -> None:
        a = client.post("/api/projects", json={"name": "Active"}).json()["id"]
        b = client.post("/api/projects", json={"name": "Archived", "is_active": False}).json()["id"]
        ids = [p["id"] for p in client.get("/api/projects?active_only=true").json()]
        assert a in ids and b not in ids

    def test_get_missing_returns_404(self, client: TestClient) -> None:
        assert client.get("/api/projects/9999").status_code == 404

    def test_update_missing_returns_404(self, client: TestClient) -> None:
        r = client.put("/api/projects/9999", json={"name": "X"})
        assert r.status_code == 404


@pytest.mark.integration
class TestClients:
    def test_create_list_update_delete(self, client: TestClient) -> None:
        r = client.post("/api/clients", json={"name": "Acme", "email": "a@b.c"})
        assert r.status_code == 201
        cid = r.json()["id"]

        listed = client.get("/api/clients").json()
        assert any(c["id"] == cid for c in listed)

        r2 = client.put(f"/api/clients/{cid}", json={"name": "Acme Inc"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "Acme Inc"

        assert client.delete(f"/api/clients/{cid}").status_code == 204
        assert client.delete(f"/api/clients/{cid}").status_code == 404

    def test_update_missing_returns_404(self, client: TestClient) -> None:
        assert client.put("/api/clients/9999", json={"name": "X"}).status_code == 404


@pytest.mark.integration
class TestCategories:
    def test_create_and_filter_by_project(self, client: TestClient) -> None:
        pid = client.post("/api/projects", json={"name": "P"}).json()["id"]
        global_id = client.post("/api/categories", json={"name": "Global"}).json()["id"]
        scoped_id = client.post("/api/categories", json={"name": "Scoped", "project_id": pid}).json()["id"]

        all_ids = [c["id"] for c in client.get("/api/categories").json()]
        assert global_id in all_ids and scoped_id in all_ids

        # Filtering by project_id returns scoped + global.
        scoped = [c["id"] for c in client.get(f"/api/categories?project_id={pid}").json()]
        assert scoped_id in scoped and global_id in scoped

    def test_update_and_delete(self, client: TestClient) -> None:
        cid = client.post("/api/categories", json={"name": "Tmp"}).json()["id"]
        client.put(f"/api/categories/{cid}", json={"name": "Renamed"})
        client.delete(f"/api/categories/{cid}")
        assert client.put(f"/api/categories/{cid}", json={"name": "Z"}).status_code == 404
