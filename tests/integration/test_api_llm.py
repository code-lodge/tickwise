"""Integration tests for /api/llm endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tickwise.classification.llm_client import ClassificationResult
from tickwise.crypto import keyring
from tickwise.db.connection import get_connection, transaction


@pytest.mark.integration
class TestConfig:
    def test_get_default_config(self, client: TestClient) -> None:
        body = client.get("/api/llm/config").json()
        assert body["provider"] == "anthropic"
        assert body["has_api_key"] is False

    def test_put_persists_api_key_in_keyring(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()

        r = client.put(
            "/api/llm/config",
            json={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "max_tokens": 200,
                "temperature": 0.0,
                "monthly_budget_cents": 500,
                "is_active": True,
                "api_key": "sk-test",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["has_api_key"] is True
        assert body["provider"] == "openai"
        # API key is never echoed back in the response payload.
        assert "api_key" not in body or body.get("api_key") in (None,)

        # Reload via GET to confirm persistence.
        body2 = client.get("/api/llm/config").json()
        assert body2["model"] == "gpt-4o-mini"
        assert body2["has_api_key"] is True

    def test_put_clears_key_when_empty_string(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
    ) -> None:
        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()
        client.put("/api/llm/config", json={"api_key": "sk-test"})
        client.put("/api/llm/config", json={"api_key": ""})
        body = client.get("/api/llm/config").json()
        assert body["has_api_key"] is False


@pytest.mark.integration
class TestUsage:
    def test_empty_usage(self, client: TestClient) -> None:
        body = client.get("/api/llm/usage").json()
        assert body["summary"]["calls"] == 0
        assert body["recent"] == []
        assert "budget" in body

    def test_summarises_logged_calls(self, client: TestClient) -> None:
        with transaction() as conn:
            conn.execute("""
                INSERT INTO llm_usage_log
                    (provider, model, prompt_tokens, completion_tokens, cost_usd, cost_cents,
                     cache_hit, classification_success)
                VALUES ('anthropic', 'haiku', 100, 50, 0.001, 0.1, 0, 1),
                       ('cache', 'cache', 0, 0, 0, 0, 1, 1)
                """)
        body = client.get("/api/llm/usage").json()
        assert body["summary"]["calls"] == 2
        assert body["summary"]["cache_hits"] == 1


@pytest.mark.integration
class TestTestEndpoint:
    def test_returns_400_when_no_api_key(self, client: TestClient) -> None:
        r = client.post("/api/llm/test", json={})
        assert r.status_code == 400

    def test_runs_classify_when_configured(self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()

        keyring.store("llm_api_key", "sk-test")
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET api_key_ref = 'llm_api_key' WHERE id = 1")

        from tickwise.api import routes_llm

        fake_client_cls = type("FakeClient", (), {})

        def _factory(*_a: object, **_kw: object) -> object:
            instance = fake_client_cls()
            instance.classify = lambda *a, **kw: ClassificationResult(  # type: ignore[attr-defined]
                project="X",
                task="development",
                confidence=0.9,
                reasoning="r",
                raw_json='{"project":"X"}',
                prompt_tokens=10,
                completion_tokens=5,
                latency_ms=20,
            )
            return instance

        monkeypatch.setattr(routes_llm, "ClaudeClient", _factory)
        r = client.post("/api/llm/test", json={"process_name": "code.exe"})
        assert r.status_code == 200
        assert r.json()["project"] == "X"


@pytest.mark.integration
class TestClassifyNow:
    def test_skips_when_no_api_key(self, client: TestClient) -> None:
        r = client.post("/api/llm/classify", json={})
        assert r.status_code == 200
        body = r.json()
        assert body["skipped"] is True
        assert body["reason"] == "no_api_key"
        assert body["stats"]["skipped_no_key"] == 1
        # No activity row was touched (we passed activity_id=0).
        assert get_connection().execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 0
