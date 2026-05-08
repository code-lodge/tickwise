"""Integration tests for /api/invoices and /api/profile."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chronolens.db.connection import transaction


def _seed_project_with_session(rate: float = 100.0, billed: int = 0) -> tuple[int, int]:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, hourly_rate, currency) VALUES (?, ?, ?)",
            ("Test", rate, "USD"),
        )
        project_id = int(cur.lastrowid or 0)
        cur = conn.execute(
            """INSERT INTO sessions (started_at, ended_at, duration_secs, project_id, is_billed)
                       VALUES (?, ?, ?, ?, ?)""",
            ("2026-05-08T09:00:00", "2026-05-08T11:00:00", 7200, project_id, billed),
        )
        return project_id, int(cur.lastrowid or 0)


@pytest.mark.integration
class TestProfile:
    def test_get_default_profile(self, client: TestClient) -> None:
        r = client.get("/api/profile")
        assert r.status_code == 200
        body = r.json()
        assert body["invoice_prefix"] == "INV"
        assert body["invoice_default_tax_rate"] == 21.0

    def test_update_profile_round_trip(self, client: TestClient) -> None:
        r = client.put(
            "/api/profile",
            json={
                "name": "Alice",
                "email": "alice@example.com",
                "company": "Acme",
                "default_currency": "EUR",
                "invoice_prefix": "ACM",
                "invoice_next_number": 5,
                "invoice_default_due_days": 30,
                "invoice_default_tax_rate": 19.0,
                "timezone": "UTC",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Alice"
        assert body["invoice_prefix"] == "ACM"


@pytest.mark.integration
class TestInvoiceLifecycle:
    def test_draft_then_create_then_pdf(self, client: TestClient) -> None:
        project_id, _ = _seed_project_with_session(rate=80.0)

        # Draft
        r = client.post(
            "/api/invoices/draft",
            json={"project_id": project_id, "from_date": "2026-05-01", "to_date": "2026-05-31"},
        )
        assert r.status_code == 200
        draft = r.json()
        assert draft["subtotal"] == pytest.approx(160.0)

        # Persist
        r = client.post(
            "/api/invoices",
            json={
                "issued_date": "2026-05-09",
                "tax_rate": 21.0,
                "currency": "USD",
                "project_id": project_id,
                "line_items": [
                    {"description": "Backend work", "hours": 2.0, "rate": 80.0},
                ],
            },
        )
        assert r.status_code == 201
        inv = r.json()
        assert inv["invoice_number"].startswith("INV-")
        assert inv["subtotal"] == 160.0
        assert inv["total"] == pytest.approx(193.6)

        # PDF
        pdf = client.get(f"/api/invoices/{inv['id']}/pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF-")

    def test_mark_sent_then_paid(self, client: TestClient) -> None:
        project_id, _ = _seed_project_with_session()
        r = client.post(
            "/api/invoices",
            json={
                "issued_date": "2026-05-09",
                "tax_rate": 0.0,
                "currency": "USD",
                "project_id": project_id,
                "line_items": [{"description": "Work", "hours": 1.0, "rate": 50.0}],
            },
        )
        invoice_id = r.json()["id"]

        # Cannot mark paid before sent
        r = client.post(f"/api/invoices/{invoice_id}/mark-paid")
        assert r.status_code == 409

        r = client.post(f"/api/invoices/{invoice_id}/mark-sent")
        assert r.status_code == 200
        assert r.json()["status"] == "sent"
        assert r.json()["sent_at"] is not None

        r = client.post(f"/api/invoices/{invoice_id}/mark-paid")
        assert r.status_code == 200
        assert r.json()["status"] == "paid"
        assert r.json()["paid_at"] is not None

    def test_session_marked_billed(self, client: TestClient) -> None:
        project_id, session_id = _seed_project_with_session()
        client.post(
            "/api/invoices",
            json={
                "issued_date": "2026-05-09",
                "tax_rate": 0.0,
                "currency": "USD",
                "project_id": project_id,
                "line_items": [
                    {"description": "Work", "hours": 2.0, "rate": 50.0, "session_id": session_id},
                ],
            },
        )
        from chronolens.db.connection import get_connection

        row = (
            get_connection()
            .execute("SELECT is_billed, invoice_id FROM sessions WHERE id = ?", (session_id,))
            .fetchone()
        )
        assert row["is_billed"] == 1
        assert row["invoice_id"] is not None

    def test_cannot_edit_sent_invoice(self, client: TestClient) -> None:
        project_id, _ = _seed_project_with_session()
        r = client.post(
            "/api/invoices",
            json={
                "issued_date": "2026-05-09",
                "tax_rate": 0.0,
                "currency": "USD",
                "project_id": project_id,
                "line_items": [{"description": "Work", "hours": 1.0, "rate": 50.0}],
            },
        )
        invoice_id = r.json()["id"]
        client.post(f"/api/invoices/{invoice_id}/mark-sent")
        r = client.put(
            f"/api/invoices/{invoice_id}",
            json={
                "issued_date": "2026-05-09",
                "tax_rate": 0.0,
                "currency": "USD",
                "line_items": [],
            },
        )
        assert r.status_code == 409

    def test_delete_paid_invoice_blocked(self, client: TestClient) -> None:
        project_id, _ = _seed_project_with_session()
        inv = client.post(
            "/api/invoices",
            json={
                "issued_date": "2026-05-09",
                "tax_rate": 0.0,
                "currency": "USD",
                "project_id": project_id,
                "line_items": [{"description": "Work", "hours": 1.0, "rate": 50.0}],
            },
        ).json()
        client.post(f"/api/invoices/{inv['id']}/mark-sent")
        client.post(f"/api/invoices/{inv['id']}/mark-paid")
        r = client.delete(f"/api/invoices/{inv['id']}")
        assert r.status_code == 409


@pytest.mark.integration
class TestClientCRUD:
    def test_create_with_address_and_tax(self, client: TestClient) -> None:
        r = client.post(
            "/api/clients",
            json={
                "name": "Acme",
                "email": "ops@acme.com",
                "address": "1 Main\nMetropolis",
                "tax_id": "EU123",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["address"].startswith("1 Main")
        assert body["tax_id"] == "EU123"
