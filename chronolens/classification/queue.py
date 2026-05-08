"""Thread-safe classification queue.

The capture loop pushes `ClassificationJob` items here whenever the screen
changes; the LLM thread (Phase 3) will pop from it. Phase 1 only implements
the producer side. The queue has a bounded size — when full, the oldest
unprocessed item is dropped so we never block the capture thread.
"""

from __future__ import annotations

import logging
import queue
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClassificationJob:
    """A single screen-change event awaiting LLM classification."""

    activity_id: int
    captured_at: datetime
    window_title: str
    process_name: str
    raw_ocr_text: str
    redacted_text: str
    phash: str


_DEFAULT_MAXSIZE = 100
_q: queue.Queue[ClassificationJob] = queue.Queue(maxsize=_DEFAULT_MAXSIZE)


def submit(job: ClassificationJob) -> None:
    """Enqueue a job; drop the oldest if the queue is full.

    Never blocks the caller — the capture loop must keep ticking even when
    the LLM is overloaded.
    """
    try:
        _q.put_nowait(job)
    except queue.Full:
        try:
            dropped = _q.get_nowait()
            logger.warning("Classification queue full, dropped activity_id=%d", dropped.activity_id)
        except queue.Empty:
            pass
        try:
            _q.put_nowait(job)
        except queue.Full:
            logger.error("Classification queue still full after drop — dropping new job %d", job.activity_id)


def take(timeout: float | None = None) -> ClassificationJob | None:
    """Block until a job is available or `timeout` elapses; returns None on timeout."""
    try:
        return _q.get(timeout=timeout)
    except queue.Empty:
        return None


def qsize() -> int:
    """Approximate queue depth — subject to producer/consumer races."""
    return _q.qsize()


def clear() -> None:
    """Drain all pending jobs (used in tests and on shutdown)."""
    while True:
        try:
            _q.get_nowait()
        except queue.Empty:
            return
