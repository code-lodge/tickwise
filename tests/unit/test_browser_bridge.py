"""Unit tests for the browser-extension bridge."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from tickwise.capture import browser_bridge
from tickwise.redaction.engine import RedactionEngine


@pytest.fixture(autouse=True)
def _reset_bridge() -> None:
    browser_bridge.clear()
    browser_bridge.set_redaction_engine(None)


@pytest.mark.unit
class TestBridge:
    def test_starts_empty(self) -> None:
        assert browser_bridge.latest() is None

    def test_update_then_latest(self) -> None:
        browser_bridge.update(
            url="https://github.com/code-lodge/tickwise",
            title="Tickwise",
            content_snippet="Some page text",
        )
        ctx = browser_bridge.latest()
        assert ctx is not None
        assert ctx.url == "https://github.com/code-lodge/tickwise"
        assert ctx.title == "Tickwise"

    def test_empty_update_ignored(self) -> None:
        browser_bridge.update(None, None, None)
        assert browser_bridge.latest() is None

    def test_clear_drops_context(self) -> None:
        browser_bridge.update(url="https://x", title="t", content_snippet=None)
        browser_bridge.clear()
        assert browser_bridge.latest() is None

    def test_stale_context_returns_none(self) -> None:
        browser_bridge.update(url="https://x", title="t", content_snippet=None)
        # Advance time well past the staleness window.
        with patch("tickwise.capture.browser_bridge.time.monotonic", return_value=time.monotonic() + 60):
            assert browser_bridge.latest() is None


@pytest.mark.unit
class TestRedactedAccess:
    def test_no_engine_returns_raw(self) -> None:
        browser_bridge.update(url="https://x.test", title="hi", content_snippet="body")
        url, title, snippet = browser_bridge.latest_redacted()
        assert url == "https://x.test"
        assert title == "hi"
        assert snippet == "body"

    def test_with_engine_redacts_email_and_secrets(self) -> None:
        engine = RedactionEngine(privacy_level=2, custom_rules=[])
        browser_bridge.set_redaction_engine(engine)
        browser_bridge.update(
            url="https://x.test/alice@example.com",
            title="Inbox — alice@example.com",
            content_snippet="user alice@example.com signed in",
        )
        url, title, snippet = browser_bridge.latest_redacted()
        assert "alice@example.com" not in (url or "")
        assert "alice@example.com" not in (title or "")
        assert "alice@example.com" not in (snippet or "")
        assert "[EMAIL]" in (title or "")

    def test_empty_when_no_context(self) -> None:
        assert browser_bridge.latest_redacted() == (None, None, None)
