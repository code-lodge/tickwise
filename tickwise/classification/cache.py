"""SHA-256-keyed LRU-ish classification cache with TTL.

The cache stores `ClassificationResult` outcomes against a fingerprint
derived from the redacted screen text + process name. A subsequent tick
that produces the same fingerprint reuses the prior classification
without an LLM round-trip.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from tickwise.classification.llm_client import ClassificationResult
from tickwise.config import DEFAULTS
from tickwise.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)


def compute_cache_key(redacted_text: str, process_name: str) -> str:
    """Stable hash for (redacted_text, process_name). 64 hex chars."""
    h = hashlib.sha256()
    h.update((process_name or "").encode("utf-8"))
    h.update(b"\x1f")
    h.update((redacted_text or "").encode("utf-8"))
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class CachedClassification:
    """A live cache hit, ready to be applied to an activity row."""

    cache_id: int
    project_id: int | None
    category_id: int | None
    description: str | None
    confidence: float | None
    llm_response: str | None


def lookup(cache_key: str) -> CachedClassification | None:
    """Return a non-expired cached classification, or None on miss/expiry."""
    now = _now_iso()
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, project_id, category_id, description, confidence, llm_response "
            "FROM classification_cache WHERE cache_key = ? AND expires_at > ?",
            (cache_key, now),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE classification_cache " "SET hit_count = hit_count + 1, last_hit_at = ? " "WHERE id = ?",
            (now, row["id"]),
        )
    return CachedClassification(
        cache_id=int(row["id"]),
        project_id=row["project_id"],
        category_id=row["category_id"],
        description=row["description"],
        confidence=row["confidence"],
        llm_response=row["llm_response"],
    )


def store(
    cache_key: str,
    result: ClassificationResult,
    *,
    project_id: int | None = None,
    category_id: int | None = None,
    ttl_hours: int | None = None,
) -> None:
    """Persist a fresh classification under `cache_key`.

    Existing rows for the same key are overwritten (a re-classification
    that disagrees with the cache resets the entry).
    """
    if not result.success:
        return
    ttl = int(ttl_hours if ttl_hours is not None else cast(int, DEFAULTS["cache_ttl_hours"]))
    expires_at = (datetime.now(tz=UTC) + timedelta(hours=ttl)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = json.dumps(
        {
            "project": result.project,
            "task": result.task,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
        }
    )
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO classification_cache
                (cache_key, project_id, category_id, description, confidence,
                 llm_response, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                project_id = excluded.project_id,
                category_id = excluded.category_id,
                description = excluded.description,
                confidence = excluded.confidence,
                llm_response = excluded.llm_response,
                expires_at = excluded.expires_at,
                hit_count = classification_cache.hit_count + 1,
                last_hit_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            """,
            (
                cache_key,
                project_id,
                category_id,
                result.reasoning or None,
                result.confidence,
                payload,
                expires_at,
            ),
        )


def purge_expired() -> int:
    """Remove expired rows. Returns the count deleted."""
    with transaction() as conn:
        cur = conn.execute("DELETE FROM classification_cache WHERE expires_at <= ?", (_now_iso(),))
    return int(cur.rowcount or 0)


def hit_rate() -> float:
    """Aggregate hit-rate across all cache rows (sum hits / total rows)."""
    conn = get_connection()
    row = conn.execute("SELECT SUM(hit_count) AS hits, COUNT(*) AS rows FROM classification_cache").fetchone()
    if not row or not row["rows"]:
        return 0.0
    hits = int(row["hits"] or 0)
    total = max(int(row["rows"]), 1)
    return hits / total


def _now_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
