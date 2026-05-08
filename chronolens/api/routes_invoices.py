"""Invoice CRUD + PDF generation + lifecycle endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from chronolens.db.connection import get_connection, transaction
from chronolens.invoices.generator import (
    allocate_invoice_number,
    build_draft,
    default_due_date,
)
from chronolens.invoices.pdf_renderer import render_html, to_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


# ─── Schemas ─────────────────────────────────────────────────────────────


class LineItemIn(BaseModel):
    description: str = Field(min_length=1)
    hours: float = Field(ge=0)
    rate: float = Field(ge=0)
    session_id: int | None = None


class LineItemOut(LineItemIn):
    id: int
    amount: float


class InvoiceIn(BaseModel):
    client_id: int | None = None
    project_id: int | None = None
    invoice_number: str | None = None
    issued_date: str
    due_date: str | None = None
    status: str = Field(default="draft", pattern="^(draft|sent|paid|overdue|cancelled)$")
    tax_rate: float = Field(default=21.0, ge=0, le=100)
    currency: str = "USD"
    notes: str | None = None
    line_items: list[LineItemIn] = Field(default_factory=list)


class InvoiceOut(BaseModel):
    id: int
    client_id: int | None
    project_id: int | None
    invoice_number: str
    issued_date: str
    due_date: str | None
    status: str
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    currency: str
    notes: str | None
    sent_at: str | None
    paid_at: str | None
    line_items: list[LineItemOut]


class DraftRequest(BaseModel):
    project_id: int
    from_date: str
    to_date: str
    rate_override: float | None = None
    tax_rate_override: float | None = None


# ─── Helpers ─────────────────────────────────────────────────────────────


def _row_to_dict(row: Any) -> dict[str, Any]:
    keys = row.keys()
    return {k: row[k] for k in keys}


def _load_invoice(invoice_id: int) -> dict[str, Any]:
    conn = get_connection()
    inv_row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if inv_row is None:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    invoice = _row_to_dict(inv_row)
    items = conn.execute(
        "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY id",
        (invoice_id,),
    ).fetchall()
    invoice["line_items"] = [_row_to_dict(i) for i in items]
    return invoice


def _recalculate_totals(invoice_id: int) -> None:
    conn = get_connection()
    rows = conn.execute(
        "SELECT amount FROM invoice_line_items WHERE invoice_id = ?",
        (invoice_id,),
    ).fetchall()
    subtotal = round(sum(float(r["amount"] or 0) for r in rows), 2)
    inv = conn.execute("SELECT tax_rate FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    tax_rate = float(inv["tax_rate"] or 0)
    tax_amount = round(subtotal * tax_rate / 100.0, 2)
    total = round(subtotal + tax_amount, 2)
    with transaction() as txn:
        txn.execute(
            "UPDATE invoices SET subtotal = ?, tax_amount = ?, total = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (subtotal, tax_amount, total, invoice_id),
        )


def _serialize(invoice: dict[str, Any]) -> InvoiceOut:
    items = [
        LineItemOut(
            id=int(it["id"]),
            description=it["description"],
            hours=float(it["hours"] or 0),
            rate=float(it["rate"] or 0),
            amount=float(it["amount"] or 0),
            session_id=int(it["session_id"]) if it.get("session_id") is not None else None,
        )
        for it in invoice.get("line_items", [])
    ]
    return InvoiceOut(
        id=int(invoice["id"]),
        client_id=int(invoice["client_id"]) if invoice.get("client_id") is not None else None,
        project_id=int(invoice["project_id"]) if invoice.get("project_id") is not None else None,
        invoice_number=invoice["invoice_number"],
        issued_date=invoice["issued_date"],
        due_date=invoice.get("due_date"),
        status=invoice["status"],
        subtotal=float(invoice["subtotal"] or 0),
        tax_rate=float(invoice["tax_rate"] or 0),
        tax_amount=float(invoice["tax_amount"] or 0),
        total=float(invoice["total"] or 0),
        currency=invoice["currency"],
        notes=invoice.get("notes"),
        sent_at=invoice.get("sent_at"),
        paid_at=invoice.get("paid_at"),
        line_items=items,
    )


# ─── Endpoints ───────────────────────────────────────────────────────────


@router.get("", response_model=list[InvoiceOut])
async def list_invoices(status: str | None = None) -> list[InvoiceOut]:
    sql = "SELECT * FROM invoices"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY issued_date DESC, id DESC"
    rows = get_connection().execute(sql, params).fetchall()
    return [_serialize(_load_invoice(int(r["id"]))) for r in rows]


@router.post("/draft")
async def draft_invoice(payload: DraftRequest) -> dict[str, Any]:
    """Build a non-persisted draft invoice from sessions in a date range."""
    try:
        draft = build_draft(
            payload.project_id,
            payload.from_date,
            payload.to_date,
            rate_override=payload.rate_override,
            tax_rate_override=payload.tax_rate_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return draft.to_dict()


@router.post("", response_model=InvoiceOut, status_code=201)
async def create_invoice(payload: InvoiceIn) -> InvoiceOut:
    invoice_number = payload.invoice_number or allocate_invoice_number()
    due = payload.due_date or default_due_date(payload.issued_date)

    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO invoices (
                client_id, project_id, invoice_number, issued_date, due_date, status,
                tax_rate, currency, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.client_id,
                payload.project_id,
                invoice_number,
                payload.issued_date,
                due,
                payload.status,
                payload.tax_rate,
                payload.currency,
                payload.notes,
            ),
        )
        invoice_id = int(cur.lastrowid or 0)
        for item in payload.line_items:
            amount = round(item.hours * item.rate, 2)
            conn.execute(
                "INSERT INTO invoice_line_items (invoice_id, session_id, description, hours, rate, amount) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (invoice_id, item.session_id, item.description, item.hours, item.rate, amount),
            )
            if item.session_id is not None:
                conn.execute(
                    "UPDATE sessions SET is_billed = 1, invoice_id = ? WHERE id = ?",
                    (invoice_id, item.session_id),
                )

    _recalculate_totals(invoice_id)
    return _serialize(_load_invoice(invoice_id))


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: int) -> InvoiceOut:
    return _serialize(_load_invoice(invoice_id))


@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(invoice_id: int, payload: InvoiceIn) -> InvoiceOut:
    existing = _load_invoice(invoice_id)
    if existing["status"] in {"sent", "paid"}:
        raise HTTPException(status_code=409, detail="Cannot edit invoice once sent or paid")

    with transaction() as conn:
        # Free any sessions that were billed against this invoice — we'll re-bill below.
        conn.execute(
            "UPDATE sessions SET is_billed = 0, invoice_id = NULL WHERE invoice_id = ?",
            (invoice_id,),
        )
        conn.execute("DELETE FROM invoice_line_items WHERE invoice_id = ?", (invoice_id,))
        conn.execute(
            """
            UPDATE invoices SET
                client_id = ?, project_id = ?, issued_date = ?, due_date = ?,
                status = ?, tax_rate = ?, currency = ?, notes = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE id = ?
            """,
            (
                payload.client_id,
                payload.project_id,
                payload.issued_date,
                payload.due_date,
                payload.status,
                payload.tax_rate,
                payload.currency,
                payload.notes,
                invoice_id,
            ),
        )
        for item in payload.line_items:
            amount = round(item.hours * item.rate, 2)
            conn.execute(
                "INSERT INTO invoice_line_items (invoice_id, session_id, description, hours, rate, amount) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (invoice_id, item.session_id, item.description, item.hours, item.rate, amount),
            )
            if item.session_id is not None:
                conn.execute(
                    "UPDATE sessions SET is_billed = 1, invoice_id = ? WHERE id = ?",
                    (invoice_id, item.session_id),
                )

    _recalculate_totals(invoice_id)
    return _serialize(_load_invoice(invoice_id))


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(invoice_id: int) -> None:
    existing = _load_invoice(invoice_id)
    if existing["status"] == "paid":
        raise HTTPException(status_code=409, detail="Cannot delete a paid invoice")
    with transaction() as conn:
        conn.execute(
            "UPDATE sessions SET is_billed = 0, invoice_id = NULL WHERE invoice_id = ?",
            (invoice_id,),
        )
        conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))


@router.post("/{invoice_id}/mark-sent", response_model=InvoiceOut)
async def mark_sent(invoice_id: int) -> InvoiceOut:
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE invoices SET status = 'sent', "
            "sent_at = COALESCE(sent_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')), "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
            "WHERE id = ? AND status IN ('draft', 'sent')",
            (invoice_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=409, detail="Invoice not in a sendable state")
    return _serialize(_load_invoice(invoice_id))


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceOut)
async def mark_paid(invoice_id: int) -> InvoiceOut:
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE invoices SET status = 'paid', "
            "paid_at = COALESCE(paid_at, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')), "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
            "WHERE id = ? AND status IN ('sent', 'paid', 'overdue')",
            (invoice_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=409, detail="Mark the invoice sent before paid")
    return _serialize(_load_invoice(invoice_id))


@router.get("/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: int) -> Response:
    invoice = _load_invoice(invoice_id)
    conn = get_connection()
    profile_row = conn.execute("SELECT * FROM freelancer_profile WHERE id = 1").fetchone()
    profile = _row_to_dict(profile_row) if profile_row else {}
    client = None
    if invoice.get("client_id"):
        client_row = conn.execute("SELECT * FROM clients WHERE id = ?", (invoice["client_id"],)).fetchone()
        client = _row_to_dict(client_row) if client_row else None
    pdf_bytes = to_pdf(invoice, profile, client)
    filename = f"{invoice['invoice_number']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{invoice_id}/preview")
async def invoice_preview(invoice_id: int) -> Response:
    invoice = _load_invoice(invoice_id)
    conn = get_connection()
    profile_row = conn.execute("SELECT * FROM freelancer_profile WHERE id = 1").fetchone()
    profile = _row_to_dict(profile_row) if profile_row else {}
    client = None
    if invoice.get("client_id"):
        client_row = conn.execute("SELECT * FROM clients WHERE id = ?", (invoice["client_id"],)).fetchone()
        client = _row_to_dict(client_row) if client_row else None
    return Response(content=render_html(invoice, profile, client), media_type="text/html; charset=utf-8")
