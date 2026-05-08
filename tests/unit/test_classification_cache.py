"""Unit tests for tickwise.classification.cache."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tickwise.classification import cache as cache_mod
from tickwise.classification.llm_client import ClassificationResult
from tickwise.db.connection import get_connection, transaction


def _result(project: str = "Alpha") -> ClassificationResult:
    return ClassificationResult(
        project=project,
        task="development",
        confidence=0.9,
        reasoning="cached reasoning",
        raw_json='{"project":"Alpha"}',
        prompt_tokens=10,
        completion_tokens=5,
        latency_ms=20,
        success=True,
    )


@pytest.mark.unit
class TestComputeCacheKey:
    def test_deterministic(self) -> None:
        a = cache_mod.compute_cache_key("hello", "vscode.exe")
        b = cache_mod.compute_cache_key("hello", "vscode.exe")
        assert a == b
        assert len(a) == 64

    def test_different_for_different_inputs(self) -> None:
        a = cache_mod.compute_cache_key("hello", "vscode.exe")
        b = cache_mod.compute_cache_key("hello", "chrome.exe")
        assert a != b


@pytest.mark.unit
class TestCacheRoundTrip:
    def test_store_then_lookup(self, tmp_db: Path) -> None:
        key = cache_mod.compute_cache_key("text", "proc")
        cache_mod.store(key, _result(), project_id=None, category_id=None)
        hit = cache_mod.lookup(key)
        assert hit is not None
        assert hit.confidence == 0.9
        assert hit.description == "cached reasoning"

    def test_lookup_miss(self, tmp_db: Path) -> None:
        assert cache_mod.lookup("nonexistent") is None

    def test_failed_results_not_stored(self, tmp_db: Path) -> None:
        bad = ClassificationResult(
            project=None,
            task=None,
            confidence=0.0,
            reasoning="",
            raw_json="",
            success=False,
            error="boom",
        )
        cache_mod.store("k", bad)
        assert cache_mod.lookup("k") is None

    def test_expired_entries_skipped(self, tmp_db: Path) -> None:
        key = "expired"
        past = (datetime.now(tz=UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO classification_cache (cache_key, expires_at, confidence, description)
                VALUES (?, ?, 0.5, 'old')
                """,
                (key, past),
            )
        assert cache_mod.lookup(key) is None

    def test_hit_count_increments(self, tmp_db: Path) -> None:
        key = "hk"
        cache_mod.store(key, _result())
        cache_mod.lookup(key)
        cache_mod.lookup(key)
        row = (
            get_connection()
            .execute("SELECT hit_count FROM classification_cache WHERE cache_key = ?", (key,))
            .fetchone()
        )
        assert row["hit_count"] >= 3  # 1 store + 2 hits

    def test_purge_expired(self, tmp_db: Path) -> None:
        past = (datetime.now(tz=UTC) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with transaction() as conn:
            conn.execute(
                "INSERT INTO classification_cache (cache_key, expires_at) VALUES ('old', ?)",
                (past,),
            )
        cache_mod.store("fresh", _result())
        purged = cache_mod.purge_expired()
        assert purged == 1
        assert cache_mod.lookup("fresh") is not None

    def test_hit_rate_no_rows(self, tmp_db: Path) -> None:
        assert cache_mod.hit_rate() == 0.0
