"""Integration tests for GET/PUT /api/settings."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestGetAllSettings:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/settings")
        assert resp.status_code == 200

    def test_returns_dict(self, client: TestClient) -> None:
        data = client.get("/api/settings").json()
        assert isinstance(data, dict)

    def test_contains_default_keys(self, client: TestClient) -> None:
        data = client.get("/api/settings").json()
        assert "capture_interval_ms" in data
        assert "privacy_level" in data

    def test_values_are_strings(self, client: TestClient) -> None:
        data = client.get("/api/settings").json()
        for v in data.values():
            assert isinstance(v, str)


@pytest.mark.integration
class TestGetSingleSetting:
    def test_known_key_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/settings/privacy_level")
        assert resp.status_code == 200

    def test_known_key_returns_value(self, client: TestClient) -> None:
        data = client.get("/api/settings/privacy_level").json()
        assert data["value"] == "2"

    def test_unknown_key_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/settings/nonexistent_key")
        assert resp.status_code == 404


@pytest.mark.integration
class TestPutSingleSetting:
    def test_update_known_key(self, client: TestClient) -> None:
        resp = client.put("/api/settings/privacy_level", json={"value": 3})
        assert resp.status_code == 200
        assert resp.json()["value"] == "3"

    def test_updated_value_persists(self, client: TestClient) -> None:
        client.put("/api/settings/capture_interval_ms", json={"value": 2000})
        data = client.get("/api/settings/capture_interval_ms").json()
        assert data["value"] == "2000"

    def test_unknown_key_returns_422(self, client: TestClient) -> None:
        resp = client.put("/api/settings/fake_key", json={"value": "x"})
        assert resp.status_code == 422


@pytest.mark.integration
class TestBulkUpdateSettings:
    def test_bulk_update_returns_200(self, client: TestClient) -> None:
        resp = client.put("/api/settings", json={"privacy_level": 1, "ocr_enabled": False})
        assert resp.status_code == 200

    def test_bulk_update_applies_all(self, client: TestClient) -> None:
        client.put("/api/settings", json={"privacy_level": 3, "capture_interval_ms": 500})
        data = client.get("/api/settings").json()
        assert data["privacy_level"] == "3"
        assert data["capture_interval_ms"] == "500"

    def test_bulk_with_unknown_key_returns_422(self, client: TestClient) -> None:
        resp = client.put("/api/settings", json={"bad_key": "x"})
        assert resp.status_code == 422
