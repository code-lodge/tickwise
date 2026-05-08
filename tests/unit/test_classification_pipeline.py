"""Unit tests for the classification pipeline (mocked LLM)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from tickwise.classification.llm_client import ClassificationResult, LLMClient, LLMError
from tickwise.classification.pipeline import ClassificationPipeline, _LLMSettings
from tickwise.classification.queue import ClassificationJob
from tickwise.db.connection import get_connection, transaction


def _job(activity_id: int = 1, ocr: str = "Working in main.py") -> ClassificationJob:
    return ClassificationJob(
        activity_id=activity_id,
        captured_at=datetime.now(tz=UTC),
        window_title="Tickwise — main.py",
        process_name="code.exe",
        raw_ocr_text=ocr,
        redacted_text=ocr,
        phash="",
    )


def _seed_activity(ocr: str = "raw") -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO activities (captured_at, ocr_text, source) VALUES (?, ?, 'pending_classification')",
            (datetime.now(tz=UTC).isoformat(), ocr),
        )
        return int(cur.lastrowid or 0)


def _success_result() -> ClassificationResult:
    return ClassificationResult(
        project="Alpha",
        task="development",
        confidence=0.85,
        reasoning="matches python file",
        raw_json='{"project":"Alpha"}',
        prompt_tokens=120,
        completion_tokens=20,
        latency_ms=50,
        success=True,
    )


def _stub_factory(client: LLMClient | None) -> object:
    def factory(_settings: _LLMSettings) -> LLMClient | None:
        return client

    return factory


@pytest.mark.unit
class TestPipeline:
    def test_skips_when_no_api_key(self, tmp_db: Path) -> None:
        activity_id = _seed_activity()
        job = _job(activity_id)
        pipeline = ClassificationPipeline(client_factory=cast(object, _stub_factory(None)))  # type: ignore[arg-type]
        result = pipeline.process_job(job)
        assert result is None
        assert pipeline.stats.skipped_no_key == 1
        row = get_connection().execute("SELECT source FROM activities WHERE id = ?", (activity_id,)).fetchone()
        assert row["source"] == "pending_classification"

    def test_full_classification_path(self, tmp_db: Path) -> None:
        activity_id = _seed_activity()
        with transaction() as conn:
            conn.execute("INSERT INTO projects (name, is_active) VALUES ('Alpha', 1)")
            conn.execute("INSERT INTO task_categories (name) VALUES ('development')")

        fake_client = MagicMock(spec=LLMClient)
        fake_client.provider = "anthropic"
        fake_client.model = "claude-haiku-4-5-20251001"
        fake_client.classify.return_value = _success_result()

        pipeline = ClassificationPipeline(client_factory=cast(object, _stub_factory(fake_client)))  # type: ignore[arg-type]
        result = pipeline.process_job(_job(activity_id))
        assert result is not None
        assert pipeline.stats.llm_calls == 1
        assert pipeline.stats.cache_hits == 0

        row = (
            get_connection()
            .execute(
                "SELECT source, project_id, category_id, confidence FROM activities WHERE id = ?",
                (activity_id,),
            )
            .fetchone()
        )
        assert row["source"] == "llm"
        assert row["project_id"] is not None
        assert row["category_id"] is not None
        assert row["confidence"] == 0.85

        usage = get_connection().execute("SELECT * FROM llm_usage_log").fetchone()
        assert usage["cache_hit"] == 0
        assert usage["classification_success"] == 1

    def test_cache_hit_on_repeat(self, tmp_db: Path) -> None:
        a1 = _seed_activity()
        a2 = _seed_activity()
        with transaction() as conn:
            conn.execute("INSERT INTO projects (name, is_active) VALUES ('Alpha', 1)")
            conn.execute("INSERT INTO task_categories (name) VALUES ('development')")

        fake_client = MagicMock(spec=LLMClient)
        fake_client.provider = "anthropic"
        fake_client.model = "claude-haiku-4-5-20251001"
        fake_client.classify.return_value = _success_result()

        pipeline = ClassificationPipeline(client_factory=cast(object, _stub_factory(fake_client)))  # type: ignore[arg-type]
        pipeline.process_job(_job(a1))
        pipeline.process_job(_job(a2))
        assert pipeline.stats.llm_calls == 1
        assert pipeline.stats.cache_hits == 1
        assert fake_client.classify.call_count == 1

    def test_llm_error_falls_back(self, tmp_db: Path) -> None:
        activity_id = _seed_activity()
        fake_client = MagicMock(spec=LLMClient)
        fake_client.provider = "anthropic"
        fake_client.model = "claude-haiku-4-5-20251001"
        fake_client.classify.side_effect = LLMError("network down")

        pipeline = ClassificationPipeline(client_factory=cast(object, _stub_factory(fake_client)))  # type: ignore[arg-type]
        result = pipeline.process_job(_job(activity_id))
        assert result is None
        assert pipeline.stats.failures == 1

        row = get_connection().execute("SELECT source FROM activities WHERE id = ?", (activity_id,)).fetchone()
        assert row["source"] == "pending_classification"

    def test_skipped_when_over_budget(self, tmp_db: Path) -> None:
        activity_id = _seed_activity()
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET monthly_budget_cents = 1, monthly_spent_cents = 999 WHERE id = 1")
        fake_client = MagicMock(spec=LLMClient)
        fake_client.provider = "anthropic"
        fake_client.model = "claude-haiku-4-5-20251001"
        fake_client.classify.return_value = _success_result()

        pipeline = ClassificationPipeline(client_factory=cast(object, _stub_factory(fake_client)))  # type: ignore[arg-type]
        result = pipeline.process_job(_job(activity_id))
        assert result is None
        assert pipeline.stats.skipped_over_budget == 1
        fake_client.classify.assert_not_called()
