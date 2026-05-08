"""Integration test: /api/status reflects the runtime CaptureLoop state."""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from chronolens import runtime


@pytest.fixture(autouse=True)
def _reset_runtime() -> Iterator[None]:
    runtime.set_capture_loop(None)
    runtime.set_session_tracker(None)
    yield
    runtime.set_capture_loop(None)
    runtime.set_session_tracker(None)


@pytest.mark.integration
class TestStatusTracking:
    def test_default_is_not_tracking(self, client: TestClient) -> None:
        body = client.get("/api/status").json()
        assert body["tracking"] is False

    def test_running_loop_marks_tracking(self, client: TestClient) -> None:
        loop = MagicMock()
        loop.is_running = True
        loop.is_paused = False
        runtime.set_capture_loop(loop)
        body = client.get("/api/status").json()
        assert body["tracking"] is True

    def test_paused_loop_marks_not_tracking(self, client: TestClient) -> None:
        loop = MagicMock()
        loop.is_running = True
        loop.is_paused = True
        runtime.set_capture_loop(loop)
        body = client.get("/api/status").json()
        assert body["tracking"] is False
