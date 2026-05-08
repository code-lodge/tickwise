"""Integration test for the /ws/browser-extension WebSocket endpoint."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from chronolens.capture import browser_bridge


@pytest.fixture(autouse=True)
def _reset_bridge() -> None:
    browser_bridge.clear()


@pytest.mark.integration
class TestBrowserExtensionWebSocket:
    def test_context_message_updates_bridge(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/browser-extension") as ws:
            hello = json.loads(ws.receive_text())
            assert hello["type"] == "connected"
            ws.send_text(
                json.dumps(
                    {
                        "type": "context",
                        "url": "https://example.com/dashboard",
                        "title": "Dashboard",
                        "content_snippet": "page text",
                    }
                )
            )
            ws.send_text(json.dumps({"type": "ping"}))
            ws.receive_text()  # pong barrier: context has been processed
            ctx = browser_bridge.latest()
            assert ctx is not None
            assert ctx.url == "https://example.com/dashboard"
            assert ctx.title == "Dashboard"

    def test_disconnect_message_clears(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/browser-extension") as ws:
            ws.receive_text()
            ws.send_text(json.dumps({"type": "context", "url": "https://x", "title": "t"}))
            ws.send_text(json.dumps({"type": "ping"}))
            ws.receive_text()  # pong — server has now drained the context message too
            assert browser_bridge.latest() is not None
            ws.send_text(json.dumps({"type": "disconnect"}))
            ws.send_text(json.dumps({"type": "ping"}))
            ws.receive_text()  # pong — server has processed the disconnect
            assert browser_bridge.latest() is None

    def test_ping_pong(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/browser-extension") as ws:
            ws.receive_text()  # connected
            ws.send_text(json.dumps({"type": "ping"}))
            reply = json.loads(ws.receive_text())
            assert reply["type"] == "pong"

    def test_invalid_json_ignored(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/browser-extension") as ws:
            ws.receive_text()
            ws.send_text("not json")
            ws.send_text(json.dumps({"type": "context", "url": "https://y"}))
            ws.send_text(json.dumps({"type": "ping"}))
            ws.receive_text()
            assert browser_bridge.latest() is not None
