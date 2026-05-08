"""Integration tests for GET /api/status."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tickwise import __version__


@pytest.mark.integration
class TestStatusEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_status_ok(self, client: TestClient) -> None:
        data = client.get("/api/status").json()
        assert data["status"] == "ok"

    def test_version_matches_package(self, client: TestClient) -> None:
        data = client.get("/api/status").json()
        assert data["version"] == __version__

    def test_uptime_is_non_negative(self, client: TestClient) -> None:
        data = client.get("/api/status").json()
        assert data["uptime_secs"] >= 0

    def test_tracking_is_false_at_startup(self, client: TestClient) -> None:
        data = client.get("/api/status").json()
        assert data["tracking"] is False
