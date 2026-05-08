"""Invoice generation — turn tracked sessions into invoice line items.

The flow:

    project_id + date range
        → query unbilled sessions in range
        → group by task category (or project if no categories)
        → produce one line item per group: hours × rate = amount
        → sum subtotal, apply tax, return DraftInvoice

Callers persist the draft via the API. Edits happen there — this module
just produces the initial structure so the user has something to refine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from tickwise.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DraftLineItem:
    description: str
    hours: float
    rate: float
    session_ids: list[int] = field(default_factory=list)

    @property
    def amount(self) -> float:
        return round(self.hours * self.rate, 2)


@dataclass(slots=True)
class DraftInvoice:
    """Pre-persistence shape — the API turns this into rows."""

    project_id: int
    client_id: int | None
    from_date: str
    to_date: str
    currency: str
    tax_rate: float
    line_items: list[DraftLineItem]

    @property
    def subtotal(self) -> float:
        return round(sum(item.amount for item in self.line_items), 2)

    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * self.tax_rate / 100.0, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax_amount, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "client_id": self.client_id,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "currency": self.currency,
            "tax_rate": self.tax_rate,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "total": self.total,
            "line_items": [
                {
                    "description": item.description,
                    "hours": round(item.hours, 2),
                    "rate": item.rate,
                    "amount": item.amount,
                    "session_ids": item.session_ids,
                }
                for item in self.line_items
            ],
        }


def build_draft(
    project_id: int,
    from_date: str,
    to_date: str,
    *,
    rate_override: float | None = None,
    tax_rate_override: float | None = None,
) -> DraftInvoice:
    """Aggregate unbilled sessions into a draft invoice."""
    conn = get_connection()
    project = conn.execute(
        "SELECT id, name, hourly_rate, currency, client_id FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    rate = rate_override if rate_override is not None else (project["hourly_rate"] or 0.0)
    currency = project["currency"] or "USD"

    profile = conn.execute("SELECT invoice_default_tax_rate FROM freelancer_profile WHERE id = 1").fetchone()
    default_tax = float(profile["invoice_default_tax_rate"]) if profile else 21.0
    tax_rate = tax_rate_override if tax_rate_override is not None else default_tax

    sessions = conn.execute(
        """
        SELECT s.id, s.duration_secs, s.description, s.category_id,
               c.name AS category_name
          FROM sessions s
          LEFT JOIN task_categories c ON c.id = s.category_id
         WHERE s.project_id = ?
           AND s.is_billed = 0
           AND s.duration_secs IS NOT NULL
           AND date(s.started_at) >= date(?)
           AND date(s.started_at) <= date(?)
         ORDER BY s.started_at
        """,
        (project_id, from_date, to_date),
    ).fetchall()

    grouped: dict[str, DraftLineItem] = {}
    for row in sessions:
        key = row["category_name"] or "General work"
        seconds = int(row["duration_secs"] or 0)
        item = grouped.setdefault(key, DraftLineItem(description=key, hours=0.0, rate=rate))
        item.hours += seconds / 3600.0
        item.session_ids.append(int(row["id"]))

    line_items = sorted(
        (item for item in grouped.values() if item.hours > 0),
        key=lambda item: item.description,
    )
    if not line_items:
        # Always return at least one row so the user has something to edit.
        line_items = [
            DraftLineItem(description=f"Work on {project['name']}", hours=0.0, rate=rate),
        ]

    return DraftInvoice(
        project_id=project_id,
        client_id=int(project["client_id"]) if project["client_id"] is not None else None,
        from_date=from_date,
        to_date=to_date,
        currency=currency,
        tax_rate=float(tax_rate),
        line_items=line_items,
    )


# ─── Invoice numbering ──────────────────────────────────────────────────


def allocate_invoice_number() -> str:
    """Atomically allocate the next invoice number from the profile counter.

    Returns a string like ``INV-2026-001``. The numeric portion is
    zero-padded to three digits so a couple of years of monthly
    invoices sort lexically correctly.
    """
    today = date.today()
    with transaction() as conn:
        row = conn.execute("SELECT invoice_prefix, invoice_next_number FROM freelancer_profile WHERE id = 1").fetchone()
        prefix = row["invoice_prefix"] if row else "INV"
        nxt = int(row["invoice_next_number"]) if row else 1
        conn.execute(
            "UPDATE freelancer_profile SET invoice_next_number = ? WHERE id = 1",
            (nxt + 1,),
        )
    return f"{prefix}-{today.year}-{nxt:03d}"


def default_due_date(issued: str | None = None) -> str:
    """Return today + profile.invoice_default_due_days as YYYY-MM-DD."""
    base = date.fromisoformat(issued) if issued else date.today()
    row = get_connection().execute("SELECT invoice_default_due_days FROM freelancer_profile WHERE id = 1").fetchone()
    days = int(row["invoice_default_due_days"]) if row else 14
    return (base + timedelta(days=days)).isoformat()
