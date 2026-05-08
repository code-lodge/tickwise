"""Unit tests for the invoice generator + PDF renderer."""

from __future__ import annotations

import pytest

from tickwise.db.connection import transaction
from tickwise.invoices.generator import (
    DraftInvoice,
    DraftLineItem,
    allocate_invoice_number,
    build_draft,
    default_due_date,
)
from tickwise.invoices.pdf_renderer import render_html, to_pdf


def _seed_project(rate: float = 75.0, name: str = "Acme Site") -> int:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, hourly_rate, currency) VALUES (?, ?, ?)",
            (name, rate, "EUR"),
        )
        return int(cur.lastrowid or 0)


def _seed_session(
    project_id: int,
    started: str = "2026-05-08T09:00:00",
    duration_secs: int = 3600,
    category_name: str | None = None,
    is_billed: int = 0,
) -> int:
    with transaction() as conn:
        category_id: int | None = None
        if category_name is not None:
            cur = conn.execute(
                "INSERT INTO task_categories (name, project_id) VALUES (?, ?)",
                (category_name, project_id),
            )
            category_id = int(cur.lastrowid or 0)
        cur = conn.execute(
            """
            INSERT INTO sessions (
                started_at, ended_at, duration_secs, project_id, category_id, is_billed
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                started,
                started.replace("T09", "T10"),
                duration_secs,
                project_id,
                category_id,
                is_billed,
            ),
        )
        return int(cur.lastrowid or 0)


@pytest.mark.unit
class TestDraftInvoice:
    def test_calculates_totals(self) -> None:
        items = [DraftLineItem("a", 2.0, 100.0), DraftLineItem("b", 1.5, 80.0)]
        inv = DraftInvoice(
            project_id=1,
            client_id=None,
            from_date="2026-05-01",
            to_date="2026-05-31",
            currency="EUR",
            tax_rate=21.0,
            line_items=items,
        )
        assert inv.subtotal == 320.0
        # 21 % of 320 = 67.20
        assert inv.tax_amount == 67.2
        assert inv.total == 387.2

    def test_zero_tax_handled(self) -> None:
        inv = DraftInvoice(
            project_id=1,
            client_id=None,
            from_date="2026-05-01",
            to_date="2026-05-31",
            currency="USD",
            tax_rate=0.0,
            line_items=[DraftLineItem("a", 1.0, 50.0)],
        )
        assert inv.tax_amount == 0.0
        assert inv.total == 50.0


@pytest.mark.unit
class TestBuildDraft:
    def test_groups_by_category(self, tmp_db) -> None:
        project_id = _seed_project()
        _seed_session(project_id, duration_secs=3600, category_name="Backend")
        _seed_session(project_id, duration_secs=1800, category_name="Backend")
        _seed_session(project_id, duration_secs=2700, category_name="Frontend")

        draft = build_draft(project_id, "2026-05-01", "2026-05-31")
        descriptions = sorted(item.description for item in draft.line_items)
        assert descriptions == ["Backend", "Frontend"]
        backend = next(item for item in draft.line_items if item.description == "Backend")
        assert backend.hours == pytest.approx(1.5)

    def test_skips_billed_sessions(self, tmp_db) -> None:
        project_id = _seed_project()
        _seed_session(project_id, is_billed=1)
        draft = build_draft(project_id, "2026-05-01", "2026-05-31")
        assert all(item.hours == 0 for item in draft.line_items)

    def test_unknown_project_raises(self, tmp_db) -> None:
        with pytest.raises(ValueError, match="not found"):
            build_draft(999, "2026-05-01", "2026-05-31")

    def test_rate_override_propagates(self, tmp_db) -> None:
        project_id = _seed_project(rate=50.0)
        _seed_session(project_id, duration_secs=3600, category_name="Work")
        draft = build_draft(project_id, "2026-05-01", "2026-05-31", rate_override=120.0)
        assert all(item.rate == 120.0 for item in draft.line_items)

    def test_returns_placeholder_when_no_sessions(self, tmp_db) -> None:
        project_id = _seed_project(name="Empty project")
        draft = build_draft(project_id, "2026-05-01", "2026-05-31")
        assert len(draft.line_items) == 1
        assert draft.line_items[0].hours == 0


@pytest.mark.unit
class TestNumbering:
    def test_allocate_increments(self, tmp_db) -> None:
        a = allocate_invoice_number()
        b = allocate_invoice_number()
        assert a != b
        assert a.startswith("INV-")
        assert b.endswith("002")

    def test_default_due_date_uses_profile(self, tmp_db) -> None:
        with transaction() as conn:
            conn.execute("UPDATE freelancer_profile SET invoice_default_due_days = 30 WHERE id = 1")
        due = default_due_date("2026-05-01")
        assert due == "2026-05-31"


@pytest.mark.unit
class TestPDF:
    def test_render_html_contains_invoice_number(self) -> None:
        invoice = {
            "invoice_number": "INV-2026-001",
            "issued_date": "2026-05-08",
            "due_date": "2026-05-22",
            "currency": "EUR",
            "tax_rate": 21.0,
            "subtotal": 200.0,
            "tax_amount": 42.0,
            "total": 242.0,
            "line_items": [{"description": "Backend", "hours": 2.0, "rate": 100.0, "amount": 200.0}],
            "notes": "Thanks for the work",
        }
        profile = {"name": "Alice", "email": "a@example.com", "iban": "NL00BANK0000000000"}
        html = render_html(invoice, profile, None)
        assert "INV-2026-001" in html
        assert "Alice" in html
        assert "Backend" in html
        assert "242.00" in html

    def test_to_pdf_returns_pdf_bytes(self) -> None:
        invoice = {
            "invoice_number": "INV-2026-001",
            "issued_date": "2026-05-08",
            "due_date": "2026-05-22",
            "currency": "EUR",
            "tax_rate": 21.0,
            "subtotal": 100.0,
            "tax_amount": 21.0,
            "total": 121.0,
            "line_items": [{"description": "Work", "hours": 1.0, "rate": 100.0, "amount": 100.0}],
            "notes": None,
        }
        out = to_pdf(invoice, {"name": "Alice", "email": "a@x.com"}, None)
        assert out.startswith(b"%PDF-")
