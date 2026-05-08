"""Integration tests for /api/reports endpoints."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tickwise.db.connection import transaction


def _seed_session(
    started: str = "2026-05-08T09:00:00",
    duration: int = 3600,
    project_id: int | None = None,
    is_billed: int = 0,
) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO sessions (started_at, ended_at, duration_secs, project_id, is_billed) "
            "VALUES (?, ?, ?, ?, ?)",
            (started, started.replace("T09", "T10"), duration, project_id, is_billed),
        )


@pytest.mark.integration
class TestGenerate:
    def test_summary_generates(self, client: TestClient) -> None:
        _seed_session()
        r = client.post(
            "/api/reports/generate",
            json={"type": "summary", "from": "2026-05-01", "to": "2026-05-31"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["type"] == "summary"
        assert body["total_seconds"] == 3600

    def test_invalid_type_rejected_by_pydantic(self, client: TestClient) -> None:
        r = client.post(
            "/api/reports/generate",
            json={"type": "weird", "from": "2026-05-01", "to": "2026-05-31"},
        )
        assert r.status_code == 422


@pytest.mark.integration
class TestExport:
    def test_csv_export(self, client: TestClient) -> None:
        _seed_session()
        r = client.post(
            "/api/reports/export",
            json={
                "type": "summary",
                "from": "2026-05-01",
                "to": "2026-05-31",
                "format": "csv",
            },
        )
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert r.text.startswith("bucket,project,hours")

    def test_json_export(self, client: TestClient) -> None:
        _seed_session()
        r = client.post(
            "/api/reports/export",
            json={
                "type": "summary",
                "from": "2026-05-01",
                "to": "2026-05-31",
                "format": "json",
            },
        )
        assert r.status_code == 200
        body = json.loads(r.text)
        assert body["type"] == "summary"

    def test_pdf_export(self, client: TestClient) -> None:
        r = client.post(
            "/api/reports/export",
            json={
                "type": "summary",
                "from": "2026-05-01",
                "to": "2026-05-31",
                "format": "pdf",
            },
        )
        assert r.status_code == 200
        assert "application/pdf" in r.headers["content-type"]
        assert r.content.startswith(b"%PDF-")

    def test_ics_requires_detailed(self, client: TestClient) -> None:
        r = client.post(
            "/api/reports/export",
            json={
                "type": "summary",
                "from": "2026-05-01",
                "to": "2026-05-31",
                "format": "ics",
            },
        )
        assert r.status_code == 422

    def test_ics_export_with_detailed(self, client: TestClient) -> None:
        _seed_session()
        r = client.post(
            "/api/reports/export",
            json={
                "type": "detailed",
                "from": "2026-05-01",
                "to": "2026-05-31",
                "format": "ics",
            },
        )
        assert r.status_code == 200
        assert "text/calendar" in r.headers["content-type"]
