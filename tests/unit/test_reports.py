"""Unit tests for the reports generator + exports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tickwise.db.connection import transaction
from tickwise.reports.csv_export import to_csv
from tickwise.reports.generator import ReportRequest, generate
from tickwise.reports.pdf_export import render_html, to_pdf


def _seed_session(
    started: datetime,
    duration: int = 3600,
    *,
    project_id: int | None = None,
    is_billed: int = 0,
) -> int:
    ended = started + timedelta(seconds=duration)
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO sessions (started_at, ended_at, duration_secs, project_id,
                                  is_billed, llm_classified)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (started.isoformat(), ended.isoformat(), duration, project_id, is_billed),
        )
        return int(cur.lastrowid or 0)


def _seed_project(name: str = "Alpha", rate: float = 95.0, currency: str = "USD") -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, hourly_rate, currency, is_active) VALUES (?, ?, ?, 1)",
            (name, rate, currency),
        )
        return int(cur.lastrowid or 0)


@pytest.mark.unit
class TestSummaryReport:
    def test_groups_by_day(self, tmp_db: Path) -> None:
        pid = _seed_project()
        d1 = datetime(2026, 5, 8, 9, 0, tzinfo=UTC)
        d2 = datetime(2026, 5, 9, 10, 0, tzinfo=UTC)
        _seed_session(d1, 3600, project_id=pid)
        _seed_session(d2, 1800, project_id=pid)

        report = generate(
            ReportRequest(
                type="summary",
                from_date="2026-05-01",
                to_date="2026-05-10",
                group_by="day",
            )
        )
        assert report["total_seconds"] == 5400
        assert report["by_project"][0]["project"] == "Alpha"
        assert {row["bucket"] for row in report["series"]} == {"2026-05-08", "2026-05-09"}

    def test_unclassified_label(self, tmp_db: Path) -> None:
        _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), 3600)
        report = generate(ReportRequest(type="summary", from_date="2026-05-01", to_date="2026-05-10", group_by="day"))
        assert report["by_project"][0]["project"] == "Unclassified"

    def test_unknown_type(self) -> None:
        with pytest.raises(ValueError):
            generate(ReportRequest(type="bogus", from_date="2026-01-01", to_date="2026-12-31"))  # type: ignore[arg-type]


@pytest.mark.unit
class TestBillingReport:
    def test_amount_uses_rate(self, tmp_db: Path) -> None:
        pid = _seed_project(rate=100.0, currency="EUR")
        _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), 3600, project_id=pid, is_billed=1)
        report = generate(ReportRequest(type="billing", from_date="2026-05-01", to_date="2026-05-31"))
        assert report["grand_total_amount"] == pytest.approx(100.0)
        assert report["by_project"][0]["currency"] == "EUR"
        assert report["by_project"][0]["billable_seconds"] == 3600

    def test_non_billable_aggregated(self, tmp_db: Path) -> None:
        pid = _seed_project()
        _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), 1800, project_id=pid, is_billed=0)
        report = generate(ReportRequest(type="billing", from_date="2026-05-01", to_date="2026-05-31"))
        assert report["by_project"][0]["non_billable_seconds"] == 1800
        assert report["by_project"][0]["amount"] == 0.0


@pytest.mark.unit
class TestActivityReport:
    def test_groups_by_category_and_project(self, tmp_db: Path) -> None:
        pid = _seed_project()
        with transaction() as conn:
            cur = conn.execute("INSERT INTO task_categories (name) VALUES ('development')")
            cat_id = int(cur.lastrowid or 0)
            conn.execute(
                "INSERT INTO sessions (started_at, duration_secs, project_id, category_id) " "VALUES (?, ?, ?, ?)",
                ("2026-05-08T09:00:00", 1800, pid, cat_id),
            )
        report = generate(ReportRequest(type="activity", from_date="2026-05-01", to_date="2026-05-31"))
        assert report["rows"][0]["category"] == "development"
        assert report["rows"][0]["project"] == "Alpha"


@pytest.mark.unit
class TestDetailedReport:
    def test_lists_sessions_in_range(self, tmp_db: Path) -> None:
        pid = _seed_project()
        _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), 600, project_id=pid)
        _seed_session(datetime(2026, 6, 1, 9, 0, tzinfo=UTC), 600, project_id=pid)
        report = generate(ReportRequest(type="detailed", from_date="2026-05-01", to_date="2026-05-31"))
        assert len(report["sessions"]) == 1


@pytest.mark.unit
class TestProductivityReport:
    def test_active_by_hour(self, tmp_db: Path) -> None:
        _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), 3600)
        report = generate(ReportRequest(type="productivity", from_date="2026-05-01", to_date="2026-05-31"))
        assert report["active_seconds"] == 3600
        assert report["active_by_hour"][9]["seconds"] == 3600


@pytest.mark.unit
class TestCSVExport:
    def test_summary_includes_header(self, tmp_db: Path) -> None:
        pid = _seed_project()
        _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), 3600, project_id=pid)
        report = generate(ReportRequest(type="summary", from_date="2026-05-01", to_date="2026-05-31"))
        out = to_csv(report)
        assert "bucket,project,hours" in out
        assert "Alpha" in out

    def test_billing_csv(self, tmp_db: Path) -> None:
        pid = _seed_project(rate=50.0)
        _seed_session(datetime(2026, 5, 8, 9, 0, tzinfo=UTC), 3600, project_id=pid, is_billed=1)
        report = generate(ReportRequest(type="billing", from_date="2026-05-01", to_date="2026-05-31"))
        out = to_csv(report)
        assert "project,currency,billable_hours" in out

    def test_unknown_type(self) -> None:
        with pytest.raises(ValueError):
            to_csv({"type": "weird"})


@pytest.mark.unit
class TestPDFExport:
    def test_render_html_includes_title(self) -> None:
        html = render_html({"type": "summary", "from": "2026-01-01", "to": "2026-01-31", "by_project": []})
        assert "<title>Time Summary</title>" in html

    def test_to_pdf_returns_bytes(self) -> None:
        pdf = to_pdf({"type": "summary", "from": "x", "to": "y", "by_project": []})
        assert pdf.startswith(b"%PDF-")
        assert b"%%EOF" in pdf
