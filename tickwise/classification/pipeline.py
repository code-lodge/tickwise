"""Local-only classification worker thread.

Pulls jobs off the classification queue (populated by the capture loop),
applies redaction, runs the keyword matcher against the combined window /
URL / browser-tab / OCR haystack, and updates the source activity row.

100% local — no LLM, no API calls, no API keys, no cost. Activities that
no project's keywords match stay at `source = unclassified`; the user can
add keywords or assign manually.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from tickwise.classification import keyword_matcher
from tickwise.classification.queue import ClassificationJob, take
from tickwise.db.connection import transaction
from tickwise.redaction.custom_rules import load_active_rules
from tickwise.redaction.engine import RedactionEngine

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineStats:
    """Counters surfaced for logs / status endpoints."""

    processed: int = 0
    keyword_matches: int = 0
    unclassified: int = 0
    failures: int = 0


@dataclass(slots=True)
class ClassificationResult:
    """Outcome of classifying one activity. Slim — no token cost, no LLM."""

    project_id: int | None
    project_name: str | None
    matched_keyword: str | None
    confidence: float


def _update_activity(
    activity_id: int,
    *,
    redacted_text: str | None,
    source: str,
    project_id: int | None = None,
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
                   category_id = NULL,
                   confidence = ?
             WHERE id = ?
            """,
            (redacted_text, source, project_id, confidence, activity_id),
        )


class ClassificationPipeline:
    """Runs redaction → keyword match → store for one job at a time."""

    def __init__(self, *, privacy_level: int | None = None) -> None:
        from tickwise.config import DEFAULTS
        from typing import cast

        self._privacy_level = (
            int(privacy_level) if privacy_level is not None else int(cast(int, DEFAULTS["privacy_level"]))
        )
        self.stats = PipelineStats()

    def process_job(self, job: ClassificationJob) -> ClassificationResult:
        """Run the pipeline for one job. Always returns a result (never None)."""
        from tickwise.capture import browser_bridge

        engine = RedactionEngine(self._privacy_level, custom_rules=load_active_rules())
        browser_bridge.set_redaction_engine(engine)
        # We redact the OCR text we *store*, but match against the raw
        # haystack — keywords like project names or URLs would otherwise
        # be stripped before matching.
        ocr_red = engine.redact(job.raw_ocr_text).redacted_text

        ctx = browser_bridge.latest()
        haystack_parts = [
            job.window_title,
            job.process_name,
            job.raw_ocr_text,
            ctx.url if ctx else None,
            ctx.title if ctx else None,
            ctx.content_snippet if ctx else None,
        ]
        haystack = " ".join(p for p in haystack_parts if p)
        hit = keyword_matcher.match_project(haystack)

        self.stats.processed += 1
        if hit is not None:
            self.stats.keyword_matches += 1
            _update_activity(
                job.activity_id,
                redacted_text=ocr_red,
                source="keyword_match",
                project_id=hit.project_id,
                confidence=1.0,
            )
            logger.debug("Keyword match: %s ← %r", hit.project_name, hit.matched_keyword)
            return ClassificationResult(
                project_id=hit.project_id,
                project_name=hit.project_name,
                matched_keyword=hit.matched_keyword,
                confidence=1.0,
            )

        self.stats.unclassified += 1
        _update_activity(
            job.activity_id,
            redacted_text=ocr_red,
            source="unclassified",
            project_id=None,
            confidence=None,
        )
        return ClassificationResult(
            project_id=None,
            project_name=None,
            matched_keyword=None,
            confidence=0.0,
        )


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
        logger.info("Classification worker started (local keyword-match mode)")

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
