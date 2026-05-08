"""Integration tests for /api/redaction endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestLevelEndpoints:
    def test_default_level(self, client: TestClient) -> None:
        body = client.get("/api/redaction/level").json()
        assert body["level"] == 2
        assert "categories" in body
        assert "EMAIL" in body["categories"]

    def test_set_level(self, client: TestClient) -> None:
        r = client.put("/api/redaction/level", json={"level": 4})
        assert r.status_code == 200
        body = client.get("/api/redaction/level").json()
        assert body["level"] == 4
        # Level 4 includes URL/CODE_BLOCK.
        assert "CODE_BLOCK" in body["categories"]

    def test_invalid_level_rejected(self, client: TestClient) -> None:
        r = client.put("/api/redaction/level", json={"level": 99})
        assert r.status_code == 422


@pytest.mark.integration
class TestPreview:
    def test_preview_redacts_email(self, client: TestClient) -> None:
        r = client.post(
            "/api/redaction/preview",
            json={"text": "Email me at alice@example.com", "level": 2},
        )
        assert r.status_code == 200
        body = r.json()
        assert "[EMAIL]" in body["redacted_text"]
        assert "EMAIL" in body["categories_hit"]
        assert body["original_length"] > body["redacted_length"]


@pytest.mark.integration
class TestCustomRules:
    def test_create_list_update_delete(self, client: TestClient) -> None:
        # Create
        r = client.post(
            "/api/redaction/rules",
            json={"pattern": "Acme", "match_mode": "contains", "replacement": "[CLIENT]"},
        )
        assert r.status_code == 201
        rule_id = r.json()["id"]

        # List
        rules = client.get("/api/redaction/rules").json()
        assert any(rule["id"] == rule_id for rule in rules)

        # Update
        r2 = client.put(
            f"/api/redaction/rules/{rule_id}",
            json={"pattern": "Acme Inc", "match_mode": "contains", "replacement": "[ACME]"},
        )
        assert r2.status_code == 200
        assert r2.json()["replacement"] == "[ACME]"

        # Delete
        r3 = client.delete(f"/api/redaction/rules/{rule_id}")
        assert r3.status_code == 204
        assert all(rule["id"] != rule_id for rule in client.get("/api/redaction/rules").json())

    def test_update_missing_returns_404(self, client: TestClient) -> None:
        r = client.put("/api/redaction/rules/9999", json={"pattern": "x"})
        assert r.status_code == 404

    def test_delete_missing_returns_404(self, client: TestClient) -> None:
        r = client.delete("/api/redaction/rules/9999")
        assert r.status_code == 404

    def test_custom_rule_applied_in_preview(self, client: TestClient) -> None:
        client.post(
            "/api/redaction/rules",
            json={"pattern": "TopSecret", "match_mode": "contains", "replacement": "[X]"},
        )
        r = client.post("/api/redaction/preview", json={"text": "TopSecret data", "level": 1})
        body = r.json()
        assert "[X]" in body["redacted_text"]
        assert "CUSTOM" in body["categories_hit"]
