"""Application-wide constants, version string, and default settings."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from chronolens.platform.paths import data_dir

APP_NAME: Final[str] = "ChronoLens"
VERSION: Final[str] = "0.1.0"

# API server
API_HOST: Final[str] = "127.0.0.1"
API_PORT: Final[int] = 19532

# Database
DB_FILENAME: Final[str] = "chronolens.db"


def db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return data_dir() / DB_FILENAME


# ─── Default settings (match spec §6 settings table) ─────────────────────────

DEFAULTS: Final[dict[str, object]] = {
    # Capture
    "capture_interval_ms": 1000,
    "phash_change_threshold": 5,
    # OCR
    "ocr_enabled": True,
    "ocr_downscale_width": 1280,
    # Session merging
    "idle_merge_threshold": 120,
    "idle_split_threshold": 300,
    "min_session_duration": 10,
    # Privacy
    "privacy_level": 2,
    # LLM cache
    "cache_ttl_hours": 24,
    # LLM redaction
    "redaction_max_chars": 800,
    # Pomodoro
    "pomodoro_work_minutes": 25,
    "pomodoro_short_break_minutes": 5,
    "pomodoro_long_break_minutes": 15,
    "pomodoro_cycles_before_long": 4,
    "pomodoro_auto_start": False,
    # Notifications
    "desktop_notifications": True,
    # Dark mode
    "dark_mode": False,
    # Cloudflare tunnel
    "cloudflare_enabled": False,
}
