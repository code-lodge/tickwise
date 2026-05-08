"""Unit tests for tickwise.classification.cost_tracker."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tickwise.classification import cost_tracker
from tickwise.classification.llm_client import ClassificationResult
from tickwise.db.connection import get_connection, transaction


def _result(success: bool = True) -> ClassificationResult:
    return ClassificationResult(
        project="P",
        task="t",
        confidence=0.9,
        reasoning="",
        raw_json="",
        prompt_tokens=1000,
        completion_tokens=200,
        latency_ms=50,
        success=success,
    )


@pytest.mark.unit
class TestEstimateCost:
    def test_known_model(self) -> None:
        cents = cost_tracker.estimate_cost_cents("anthropic", "claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
        # 80c input + 400c output per 1M tokens.
        assert cents == pytest.approx(480.0)

    def test_unknown_model_uses_default(self) -> None:
        cents = cost_tracker.estimate_cost_cents("unknown", "x", 1_000_000, 1_000_000)
        assert cents == pytest.approx(600.0)


@pytest.mark.unit
class TestLogUsage:
    def test_records_row(self, tmp_db: Path) -> None:
        cost_tracker.log_usage("anthropic", "claude-haiku-4-5-20251001", _result())
        rows = get_connection().execute("SELECT * FROM llm_usage_log").fetchall()
        assert len(rows) == 1
        assert rows[0]["provider"] == "anthropic"
        assert rows[0]["cache_hit"] == 0
        assert rows[0]["cost_cents"] > 0

    def test_cache_hit_zero_cost(self, tmp_db: Path) -> None:
        cost_tracker.log_usage("cache", "cache", _result(), cache_hit=True)
        row = get_connection().execute("SELECT cost_cents FROM llm_usage_log").fetchone()
        assert row["cost_cents"] == 0

    def test_increments_monthly_spent(self, tmp_db: Path) -> None:
        cost_tracker.log_usage("anthropic", "claude-haiku-4-5-20251001", _result())
        spent_row = get_connection().execute("SELECT monthly_spent_cents FROM llm_config WHERE id = 1").fetchone()
        assert spent_row["monthly_spent_cents"] > 0


@pytest.mark.unit
class TestBudget:
    def test_under_budget(self, tmp_db: Path) -> None:
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET monthly_budget_cents = 1000, monthly_spent_cents = 100 WHERE id = 1")
        state = cost_tracker.current_budget_state()
        assert state.over_budget is False
        assert state.spent_cents == 100.0

    def test_over_budget(self, tmp_db: Path) -> None:
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET monthly_budget_cents = 100, monthly_spent_cents = 150 WHERE id = 1")
        state = cost_tracker.current_budget_state()
        assert state.over_budget is True

    def test_zero_budget_unlimited(self, tmp_db: Path) -> None:
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET monthly_budget_cents = 0, monthly_spent_cents = 999999 WHERE id = 1")
        state = cost_tracker.current_budget_state()
        assert state.over_budget is False


@pytest.mark.unit
class TestResetMonthlySpend:
    def test_resets_on_configured_day(self, tmp_db: Path) -> None:
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET budget_reset_day = 15, monthly_spent_cents = 250 WHERE id = 1")
        # Force "today" to be the reset day.
        when = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        assert cost_tracker.reset_monthly_spend_if_due(when) is True
        spent = (
            get_connection()
            .execute("SELECT monthly_spent_cents FROM llm_config WHERE id = 1")
            .fetchone()["monthly_spent_cents"]
        )
        assert spent == 0

    def test_no_reset_other_days(self, tmp_db: Path) -> None:
        with transaction() as conn:
            conn.execute("UPDATE llm_config SET budget_reset_day = 1, monthly_spent_cents = 250 WHERE id = 1")
        when = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)
        assert cost_tracker.reset_monthly_spend_if_due(when) is False
