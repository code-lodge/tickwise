"""Process-wide store for the latest browser context.

The browser extension pushes URL + tab title (+ optional content
snippet) over WebSocket. The capture loop and classification pipeline
read it on demand. Context older than `_STALENESS_SECS` is treated as
absent so a closed browser doesn't pollute classifications forever.

The redaction engine is applied here so the rest of the pipeline never
sees the raw URL — everything downstream stays consistent with the
configured privacy level.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from chronolens.redaction.engine import RedactionEngine

logger = logging.getLogger(__name__)

_STALENESS_SECS = 5.0


@dataclass(frozen=True, slots=True)
class BrowserContext:
    url: str | None
    title: str | None
    content_snippet: str | None
    received_at: float


_lock = threading.Lock()
_latest: BrowserContext | None = None
_redaction_engine: RedactionEngine | None = None


def set_redaction_engine(engine: RedactionEngine | None) -> None:
    """Inject the engine the bridge uses to redact incoming context."""
    global _redaction_engine
    _redaction_engine = engine


def update(url: str | None, title: str | None, content_snippet: str | None) -> None:
    """Replace the cached browser context with a fresh sample."""
    global _latest
    if not (url or title or content_snippet):
        return
    with _lock:
        _latest = BrowserContext(
            url=url,
            title=title,
            content_snippet=content_snippet,
            received_at=time.monotonic(),
        )


def clear() -> None:
    """Forget the cached context (used on extension disconnect)."""
    global _latest
    with _lock:
        _latest = None


def latest() -> BrowserContext | None:
    """Return the cached context if still fresh, else None."""
    with _lock:
        ctx = _latest
    if ctx is None:
        return None
    if time.monotonic() - ctx.received_at > _STALENESS_SECS:
        return None
    return ctx


def latest_redacted() -> tuple[str | None, str | None, str | None]:
    """Return (url, title, snippet) with redaction applied where possible."""
    ctx = latest()
    if ctx is None:
        return (None, None, None)
    engine = _redaction_engine
    if engine is None:
        return (ctx.url, ctx.title, ctx.content_snippet)
    url = engine.redact(ctx.url).redacted_text if ctx.url else None
    title = engine.redact(ctx.title).redacted_text if ctx.title else None
    snippet = engine.redact(ctx.content_snippet).redacted_text if ctx.content_snippet else None
    return (url, title, snippet)
