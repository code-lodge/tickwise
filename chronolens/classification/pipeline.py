"""End-to-end classification worker thread.

Pulls jobs off the classification queue (populated by the capture loop),
applies redaction, checks the cache, calls the configured LLM if needed,
logs token cost, and updates the source `activities` row with the
resulting project / category / confidence / source.

The worker runs in a daemon thread; one instance per process. If no API
key is configured or the monthly budget is exhausted, jobs are
acknowledged but the row stays at `source = pending_classification` so
the user can re-classify later.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from chronolens.classification import cache as cache_mod
from chronolens.classification import cost_tracker
from chronolens.classification.claude_client import ClaudeClient
from chronolens.classification.llm_client import (
    ClassificationResult,
    LLMClient,
    LLMError,
)
from chronolens.classification.openai_client import OpenAIClient
from chronolens.classification.prompts import (
    SYSTEM_PROMPT,
    ClassificationContext,
    ProjectChoice,
    build_user_prompt,
)
from chronolens.classification.queue import ClassificationJob, take
from chronolens.config import DEFAULTS
from chronolens.crypto import keyring
from chronolens.db.connection import get_connection, transaction
from chronolens.redaction.custom_rules import load_active_rules
from chronolens.redaction.engine import RedactionEngine

logger = logging.getLogger(__name__)


# ─── helpers ─────────────────────────────────────────────────────────────


@dataclass(slots=True)
class _LLMSettings:
    """In-memory snapshot of the singleton llm_config row + API key."""

    provider: str
    model: str
    api_key: str | None
    max_tokens: int
    temperature: float
    is_active: bool


def _load_settings() -> _LLMSettings:
    row = (
        get_connection()
        .execute(
            "SELECT provider, model, api_key_ref, max_tokens, temperature, is_active " "FROM llm_config WHERE id = 1"
        )
        .fetchone()
    )
    if row is None:
        return _LLMSettings("anthropic", "claude-haiku-4-5-20251001", None, 256, 0.0, False)
    api_key = None
    if row["api_key_ref"]:
        api_key = keyring.retrieve(str(row["api_key_ref"]))
    return _LLMSettings(
        provider=str(row["provider"]),
        model=str(row["model"]),
        api_key=api_key,
        max_tokens=int(row["max_tokens"] or 256),
        temperature=float(row["temperature"] or 0.0),
        is_active=bool(row["is_active"]),
    )


def _build_client(settings: _LLMSettings) -> LLMClient | None:
    if not settings.is_active or not settings.api_key:
        return None
    if settings.provider == "openai":
        return OpenAIClient(
            settings.api_key,
            settings.model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
    return ClaudeClient(
        settings.api_key,
        settings.model,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )


def _load_projects() -> list[ProjectChoice]:
    rows = (
        get_connection()
        .execute(
            "SELECT p.name AS name, c.name AS client, p.is_active AS is_active "
            "FROM projects p LEFT JOIN clients c ON p.client_id = c.id"
        )
        .fetchall()
    )
    return [ProjectChoice(name=row["name"], client=row["client"], is_active=bool(row["is_active"])) for row in rows]


def _load_task_categories() -> list[str]:
    rows = get_connection().execute("SELECT name FROM task_categories ORDER BY id").fetchall()
    return [row["name"] for row in rows]


def _resolve_project_id(name: str | None) -> int | None:
    if not name:
        return None
    row = get_connection().execute("SELECT id FROM projects WHERE name = ? AND is_active = 1", (name,)).fetchone()
    return int(row["id"]) if row else None


def _resolve_category_id(name: str | None) -> int | None:
    if not name:
        return None
    row = get_connection().execute("SELECT id FROM task_categories WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row else None


def _update_activity(
    activity_id: int,
    *,
    redacted_text: str | None,
    source: str,
    project_id: int | None = None,
    category_id: int | None = None,
    confidence: float | None = None,
) -> None:
    if not activity_id:
        return
    with transaction() as conn:
        conn.execute(
            """
            UPDATE activities
            SET redacted_text = COALESCE(?, redacted_text),
                source = ?,
                project_id = ?,
                category_id = ?,
                confidence = ?
            WHERE id = ?
            """,
            (
                redacted_text,
                source,
                project_id,
                category_id,
                confidence,
                activity_id,
            ),
        )


# ─── public API: classify a single job, the worker thread ─────────────────


@dataclass(slots=True)
class PipelineStats:
    """Counters surfaced by the worker for the API and logs."""

    processed: int = 0
    cache_hits: int = 0
    llm_calls: int = 0
    failures: int = 0
    skipped_no_key: int = 0
    skipped_over_budget: int = 0


_DEFAULT_TASK_CATEGORIES = ("development", "meeting", "research", "admin", "communication")


class ClassificationPipeline:
    """Runs the redact → cache → LLM → store flow for one job at a time."""

    def __init__(
        self,
        *,
        client_factory: Callable[[_LLMSettings], LLMClient | None] = _build_client,
        privacy_level: int | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._privacy_level = (
            int(privacy_level) if privacy_level is not None else int(cast(int, DEFAULTS["privacy_level"]))
        )
        self.stats = PipelineStats()

    def process_job(self, job: ClassificationJob) -> ClassificationResult | None:
        """Run the full pipeline for one job. Returns the result or None on skip."""
        from chronolens.capture import browser_bridge

        engine = RedactionEngine(self._privacy_level, custom_rules=load_active_rules())
        browser_bridge.set_redaction_engine(engine)
        title_red = engine.redact(job.window_title).redacted_text
        ocr_red = engine.redact(job.raw_ocr_text).redacted_text

        cache_key = cache_mod.compute_cache_key(ocr_red, job.process_name)
        hit = cache_mod.lookup(cache_key)
        if hit is not None:
            self.stats.processed += 1
            self.stats.cache_hits += 1
            _update_activity(
                job.activity_id,
                redacted_text=ocr_red,
                source="llm",
                project_id=hit.project_id,
                category_id=hit.category_id,
                confidence=hit.confidence,
            )
            cached_result = ClassificationResult(
                project=None,
                task=None,
                confidence=hit.confidence or 0.0,
                reasoning=hit.description or "",
                raw_json=hit.llm_response or "",
            )
            cost_tracker.log_usage("cache", "cache", cached_result, cache_hit=True)
            return cached_result

        settings = _load_settings()
        client = self._client_factory(settings)
        if client is None:
            self.stats.processed += 1
            self.stats.skipped_no_key += 1
            _update_activity(job.activity_id, redacted_text=ocr_red, source="pending_classification")
            return None

        budget = cost_tracker.current_budget_state()
        if budget.over_budget:
            self.stats.processed += 1
            self.stats.skipped_over_budget += 1
            _update_activity(job.activity_id, redacted_text=ocr_red, source="pending_classification")
            return None

        from chronolens.capture import browser_bridge

        url_red, browser_title_red, _ = browser_bridge.latest_redacted()
        context = ClassificationContext(
            process_name=job.process_name,
            redacted_title=title_red,
            redacted_ocr_text=ocr_red,
            redacted_url=url_red,
            redacted_browser_title=browser_title_red,
        )
        user_prompt = build_user_prompt(
            context,
            _load_projects(),
            _load_task_categories() or list(_DEFAULT_TASK_CATEGORIES),
        )
        try:
            result = client.classify(SYSTEM_PROMPT, user_prompt)
        except LLMError as exc:
            logger.warning("LLM call failed: %s", exc)
            self.stats.processed += 1
            self.stats.failures += 1
            _update_activity(job.activity_id, redacted_text=ocr_red, source="pending_classification")
            cost_tracker.log_usage(
                client.provider,
                client.model,
                ClassificationResult(
                    project=None,
                    task=None,
                    confidence=0.0,
                    reasoning="",
                    raw_json="",
                    success=False,
                    error=str(exc),
                ),
            )
            return None

        self.stats.processed += 1
        self.stats.llm_calls += 1
        cost_tracker.log_usage(client.provider, client.model, result)
        if result.success:
            project_id = _resolve_project_id(result.project)
            category_id = _resolve_category_id(result.task)
            cache_mod.store(
                cache_key,
                result,
                project_id=project_id,
                category_id=category_id,
            )
            _update_activity(
                job.activity_id,
                redacted_text=ocr_red,
                source="llm",
                project_id=project_id,
                category_id=category_id,
                confidence=result.confidence,
            )
        else:
            _update_activity(job.activity_id, redacted_text=ocr_red, source="pending_classification")
        return result


# ─── worker thread wrapper ───────────────────────────────────────────────


class ClassificationWorker:
    """Background thread that pulls from the queue and runs the pipeline."""

    def __init__(self, pipeline: ClassificationPipeline | None = None) -> None:
        self.pipeline = pipeline or ClassificationPipeline()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="classifier", daemon=True)
        self._thread.start()
        logger.info("Classification worker started")

    def stop(self, join_timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=join_timeout)
        logger.info("Classification worker stopped")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop.is_set():
            job = take(timeout=1.0)
            if job is None:
                continue
            try:
                self.pipeline.process_job(job)
            except Exception:
                logger.exception("classification pipeline crashed on job")
                self.pipeline.stats.failures += 1
