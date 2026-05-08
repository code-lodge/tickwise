"""Token-cost estimation, usage logging, and monthly budget enforcement.

Pricing tables are inlined as cents-per-million-tokens; values match
public list prices on each provider's site at time of writing. Update
when providers re-price — the table is the single source of truth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from chronolens.classification.llm_client import ClassificationResult
from chronolens.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ModelPrice:
    """USD cents per 1M tokens, for input and output respectively."""

    input_per_m: float
    output_per_m: float


# (provider, model) → price.  Unknown models fall back to _DEFAULT_PRICE.
_PRICE_TABLE: dict[tuple[str, str], _ModelPrice] = {
    ("anthropic", "claude-haiku-4-5-20251001"): _ModelPrice(80.0, 400.0),
    ("anthropic", "claude-sonnet-4-6"): _ModelPrice(300.0, 1500.0),
    ("anthropic", "claude-opus-4-7"): _ModelPrice(1500.0, 7500.0),
    ("openai", "gpt-4o-mini"): _ModelPrice(15.0, 60.0),
    ("openai", "gpt-4o"): _ModelPrice(250.0, 1000.0),
}

_DEFAULT_PRICE = _ModelPrice(input_per_m=100.0, output_per_m=500.0)


def estimate_cost_cents(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return the estimated cost in USD cents for one classification call."""
    price = _PRICE_TABLE.get((provider, model), _DEFAULT_PRICE)
    return (prompt_tokens / 1_000_000.0) * price.input_per_m + (completion_tokens / 1_000_000.0) * price.output_per_m


def log_usage(
    provider: str,
    model: str,
    result: ClassificationResult,
    *,
    cache_hit: bool = False,
    session_id: int | None = None,
) -> float:
    """Insert a `llm_usage_log` row; return the cost in cents we charged."""
    cost_cents = (
        0.0 if cache_hit else estimate_cost_cents(provider, model, result.prompt_tokens, result.completion_tokens)
    )
    cost_usd = cost_cents / 100.0
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO llm_usage_log
                (session_id, provider, model, prompt_tokens, completion_tokens,
                 cost_usd, cost_cents, latency_ms, cache_hit, classification_success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                provider,
                model,
                result.prompt_tokens,
                result.completion_tokens,
                cost_usd,
                cost_cents,
                result.latency_ms,
                1 if cache_hit else 0,
                1 if result.success else 0,
            ),
        )
        if cost_cents > 0:
            conn.execute(
                "UPDATE llm_config SET monthly_spent_cents = monthly_spent_cents + ? WHERE id = 1",
                (cost_cents,),
            )
    return cost_cents


@dataclass(frozen=True, slots=True)
class BudgetState:
    """Snapshot of the monthly LLM budget for status displays."""

    spent_cents: float
    budget_cents: int
    over_budget: bool


def current_budget_state() -> BudgetState:
    """Read current spend / budget from `llm_config`."""
    row = (
        get_connection()
        .execute("SELECT monthly_spent_cents, monthly_budget_cents FROM llm_config WHERE id = 1")
        .fetchone()
    )
    if row is None:
        return BudgetState(0.0, 0, False)
    spent = float(row["monthly_spent_cents"] or 0.0)
    budget = int(row["monthly_budget_cents"] or 0)
    over = budget > 0 and spent >= budget
    return BudgetState(spent, budget, over)


def reset_monthly_spend_if_due(now: datetime | None = None) -> bool:
    """If today is the configured `budget_reset_day`, zero `monthly_spent_cents`.

    Returns True iff the counter was actually reset. Idempotent within a
    given UTC day — running twice on the same day is a no-op because we
    only reset when the stored spend is non-zero.
    """
    moment = now or datetime.now(tz=UTC)
    row = (
        get_connection().execute("SELECT budget_reset_day, monthly_spent_cents FROM llm_config WHERE id = 1").fetchone()
    )
    if row is None:
        return False
    reset_day = int(row["budget_reset_day"] or 1)
    if moment.day != reset_day or float(row["monthly_spent_cents"] or 0.0) == 0.0:
        return False
    with transaction() as conn:
        conn.execute("UPDATE llm_config SET monthly_spent_cents = 0 WHERE id = 1")
    return True
