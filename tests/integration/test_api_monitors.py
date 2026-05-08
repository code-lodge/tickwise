"""Integration tests for /api/monitors."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tickwise.capture.screenshot import MonitorInfo


def _fake_detect():
    return [
        {"index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080},
        {"index": 2, "left": 1920, "top": 0, "width": 2560, "height": 1440},
    ]


@pytest.mark.integration
class TestListMonitors:
    def test_returns_detected_monitors(self, client: TestClient) -> None:
        with patch(
            "tickwise.api.routes_monitors._detect_monitors",
            return_value=_fake_detect(),
        ):
            r = client.get("/api/monitors")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 2
        assert rows[0]["index"] == 1
        assert rows[1]["width"] == 2560
        # First monitor defaults to is_primary
        assert rows[0]["is_primary"] is True

    def test_handles_no_monitors(self, client: TestClient) -> None:
        with patch("tickwise.api.routes_monitors._detect_monitors", return_value=[]):
            r = client.get("/api/monitors")
        assert r.status_code == 200
        assert r.json() == []


@pytest.mark.integration
class TestUpdateMonitor:
    def test_update_persists(self, client: TestClient) -> None:
        with patch(
            "tickwise.api.routes_monitors._detect_monitors",
            return_value=_fake_detect(),
        ):
            r = client.put(
                "/api/monitors/2",
                json={"label": "Right display", "enabled": False, "is_primary": False},
            )
            assert r.status_code == 200
            r = client.get("/api/monitors")
        rows = {m["index"]: m for m in r.json()}
        assert rows[2]["label"] == "Right display"
        assert rows[2]["enabled"] is False

    def test_setting_primary_clears_others(self, client: TestClient) -> None:
        with patch(
            "tickwise.api.routes_monitors._detect_monitors",
            return_value=_fake_detect(),
        ):
            client.put("/api/monitors/1", json={"enabled": True, "is_primary": True})
            client.put("/api/monitors/2", json={"enabled": True, "is_primary": True})
            r = client.get("/api/monitors")
        rows = {m["index"]: m for m in r.json()}
        assert rows[1]["is_primary"] is False
        assert rows[2]["is_primary"] is True

    def test_invalid_index_rejected(self, client: TestClient) -> None:
        r = client.put("/api/monitors/0", json={"enabled": True})
        assert r.status_code == 422


@pytest.mark.integration
class TestDisconnectedMonitor:
    def test_can_save_prefs_for_disconnected(self, client: TestClient) -> None:
        # Detect returns nothing — but the user can still save a preference for
        # a monitor they intend to use later.
        with patch("tickwise.api.routes_monitors._detect_monitors", return_value=[]):
            r = client.put(
                "/api/monitors/3",
                json={"label": "On the road", "enabled": True, "is_primary": False},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["index"] == 3
        assert body["label"] == "On the road"
        assert body["width"] == 0  # synthetic — not currently connected


@pytest.mark.unit
def test_monitor_info_contains_smoke():
    """Sanity check that MonitorInfo is importable from screenshot."""
    m = MonitorInfo(index=1, left=0, top=0, width=100, height=100)
    assert m.contains(50, 50)
