"""Unit tests for tickwise.config."""

from __future__ import annotations

import pytest

from tickwise import config


@pytest.mark.unit
class TestConfigConstants:
    def test_version_is_semver(self) -> None:
        parts = config.VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_api_host_is_loopback(self) -> None:
        assert config.API_HOST == "127.0.0.1"

    def test_api_port(self) -> None:
        assert config.API_PORT == 19532

    def test_defaults_keys_present(self) -> None:
        required = {
            "capture_interval_ms",
            "phash_change_threshold",
            "ocr_enabled",
            "ocr_downscale_width",
            "idle_merge_threshold",
            "idle_split_threshold",
            "min_session_duration",
            "privacy_level",
            "cache_ttl_hours",
            "pomodoro_work_minutes",
            "pomodoro_short_break_minutes",
            "pomodoro_long_break_minutes",
            "pomodoro_cycles_before_long",
        }
        assert required.issubset(config.DEFAULTS.keys())

    def test_default_capture_interval(self) -> None:
        assert config.DEFAULTS["capture_interval_ms"] == 1000

    def test_default_privacy_level(self) -> None:
        assert config.DEFAULTS["privacy_level"] == 2

    def test_default_ocr_downscale_width(self) -> None:
        assert config.DEFAULTS["ocr_downscale_width"] == 1280
