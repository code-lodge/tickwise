"""Integration test for migration 002 — activity.source column."""

from __future__ import annotations

from pathlib import Path

import pytest

from chronolens.db.connection import get_connection


@pytest.mark.integration
class TestActivitiesSourceColumn:
    def test_column_exists_after_init(self, tmp_db: Path) -> None:
        conn = get_connection()
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
        assert "source" in cols

    def test_default_is_pending_classification(self, tmp_db: Path) -> None:
        conn = get_connection()
        conn.execute("INSERT INTO activities (captured_at) VALUES (?)", ("2026-05-08T09:00:00Z",))
        conn.commit()
        row = conn.execute("SELECT source FROM activities").fetchone()
        assert row["source"] == "pending_classification"

    def test_source_index_exists(self, tmp_db: Path) -> None:
        conn = get_connection()
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='activities'").fetchall()
        assert any(r["name"] == "idx_activities_source" for r in rows)

    def test_schema_version_advanced(self, tmp_db: Path) -> None:
        conn = get_connection()
        row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
        assert row["v"] >= 2
