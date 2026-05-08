"""Integration tests for /api/onboarding/state and /api/backup/export."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tickwise.db.connection import transaction


@pytest.mark.integration
class TestOnboardingState:
    def test_fresh_install_flags_everything(self, client: TestClient) -> None:
        # Fresh DB: no api key, empty profile, no projects.
        # The settings table has privacy_level seeded so needs_privacy_choice is False.
        r = client.get("/api/onboarding/state")
        assert r.status_code == 200
        body = r.json()
        assert body["needs_llm_setup"] is True
        assert body["needs_profile"] is True
        assert body["needs_first_project"] is True
        assert body["complete"] is False

    def test_completed_setup_clears_flags(self, client: TestClient) -> None:
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET api_key_ref = 'kr_alias', is_active = 1 WHERE id = 1")
            conn.execute("UPDATE freelancer_profile SET name = 'Alice', email = 'a@x' WHERE id = 1")
            conn.execute("INSERT INTO projects (name, is_active) VALUES ('Acme', 1)")
        r = client.get("/api/onboarding/state")
        assert r.status_code == 200
        body = r.json()
        assert body["complete"] is True
        assert body["needs_llm_setup"] is False
        assert body["needs_profile"] is False
        assert body["needs_first_project"] is False


@pytest.mark.integration
class TestBackupExport:
    def test_export_returns_json_with_expected_tables(self, client: TestClient) -> None:
        # Seed at least one row per a couple of important tables.
        with transaction() as conn:
            conn.execute("INSERT INTO clients (name) VALUES ('Acme Corp')")
            conn.execute("INSERT INTO projects (name) VALUES ('Acme Site')")

        r = client.get("/api/backup/export")
        assert r.status_code == 200
        assert "application/json" in r.headers["content-type"]
        assert r.headers["content-disposition"].startswith("attachment; filename=tickwise-backup-")
        payload = json.loads(r.text)
        assert "tables" in payload
        assert "projects" in payload["tables"]
        assert "clients" in payload["tables"]
        assert any(c["name"] == "Acme Corp" for c in payload["tables"]["clients"])
        # Schema version is recorded so a future restorer can refuse downgrades.
        assert payload["schema_version"] >= 1
        # Confirm exclusions
        assert "activities" not in payload["tables"]
        assert "mobile_auth_tokens" not in payload["tables"]
        assert "classification_cache" not in payload["tables"]
