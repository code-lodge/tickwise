"""Integration tests for database schema initialisation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tickwise.db.connection import get_connection
from tickwise.db.schema import SCHEMA_VERSION


@pytest.mark.integration
class TestSchemaInit:
    def test_schema_version_seeded(self, tmp_db: Path) -> None:
        conn = get_connection()
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        assert row is not None
        assert int(row[0]) == SCHEMA_VERSION

    def test_settings_table_seeded_with_defaults(self, tmp_db: Path) -> None:
        conn = get_connection()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        settings = {r["key"]: r["value"] for r in rows}
        assert "capture_interval_ms" in settings
        assert settings["capture_interval_ms"] == "1000"
        assert settings["privacy_level"] == "2"
        assert settings["ocr_enabled"] == "true"

    def test_freelancer_profile_singleton_exists(self, tmp_db: Path) -> None:
        conn = get_connection()
        row = conn.execute("SELECT id FROM freelancer_profile WHERE id = 1").fetchone()
        assert row is not None

    def test_llm_config_singleton_exists(self, tmp_db: Path) -> None:
        conn = get_connection()
        row = conn.execute("SELECT id FROM llm_config WHERE id = 1").fetchone()
        assert row is not None

    def test_foreign_keys_enforced(self, tmp_db: Path) -> None:
        conn = get_connection()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO sessions(started_at, project_id) VALUES ('2024-01-01T00:00:00Z', 9999)")
            conn.commit()

    def test_wal_mode_active(self, tmp_db: Path) -> None:
        conn = get_connection()
        row = conn.execute("PRAGMA journal_mode").fetchone()
        assert row is not None
        assert row[0] == "wal"

    def test_idempotent_init(self, tmp_db: Path) -> None:
        """Calling init_db() twice must not raise or duplicate data."""
        from tickwise.db.schema import init_db

        init_db()
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
        assert count == SCHEMA_VERSION
