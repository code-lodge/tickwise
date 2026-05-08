"""Invoice PDF rendering.

Prefers WeasyPrint when present (clean HTML/CSS layout, real typography,
embedded logos). Falls back to a hand-rolled stdlib PDF so test
environments and slim containers still produce a valid file.

The HTML template lives next to this module so it can be customised
without code changes. CSS is intentionally simple — WeasyPrint chokes
on cutting-edge layout.
"""

from __future__ import annotations

import logging
from html import escape
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def to_pdf(invoice: dict[str, Any], profile: dict[str, Any], client: dict[str, Any] | None) -> bytes:
    """Render an invoice to PDF bytes."""
    html = render_html(invoice, profile, client)
    try:
        from weasyprint import HTML
    except ImportError:
        return _render_fallback_pdf(invoice, profile, client)
    return bytes(HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf() or b"")


def render_html(invoice: dict[str, Any], profile: dict[str, Any], client: dict[str, Any] | None) -> str:
    """Inline-render the invoice HTML — used by both the PDF path and the dashboard preview."""
    template = (_TEMPLATE_DIR / "default.html").read_text(encoding="utf-8")
    css = (_TEMPLATE_DIR / "default.css").read_text(encoding="utf-8")
    line_rows = "".join(
        f"<tr>"
        f"<td>{escape(item.get('description', ''))}</td>"
        f"<td class='num'>{float(item.get('hours', 0)):.2f}</td>"
        f"<td class='num'>{float(item.get('rate', 0)):.2f}</td>"
        f"<td class='num'>{float(item.get('amount', 0)):.2f}</td>"
        f"</tr>"
        for item in invoice.get("line_items", [])
    )
    logo_block = ""
    logo_path = profile.get("logo_path")
    if logo_path and Path(logo_path).is_file():
        logo_block = f"<img class='logo' src='file://{escape(str(Path(logo_path).resolve()))}' alt='logo'/>"

    return template.format(
        css=css,
        logo=logo_block,
        from_name=escape(profile.get("name") or ""),
        from_company=escape(profile.get("company") or ""),
        from_address=escape(profile.get("address") or "").replace("\n", "<br>"),
        from_email=escape(profile.get("email") or ""),
        from_tax_id=escape(profile.get("tax_id") or ""),
        from_iban=escape(profile.get("iban") or ""),
        from_bank=escape(profile.get("bank_name") or ""),
        to_name=escape((client or {}).get("name") or ""),
        to_address=escape((client or {}).get("address") or "").replace("\n", "<br>"),
        to_email=escape((client or {}).get("email") or ""),
        to_tax_id=escape((client or {}).get("tax_id") or ""),
        invoice_number=escape(invoice.get("invoice_number") or ""),
        issued_date=escape(invoice.get("issued_date") or ""),
        due_date=escape(invoice.get("due_date") or ""),
        currency=escape(invoice.get("currency") or "USD"),
        line_rows=line_rows,
        subtotal=f"{float(invoice.get('subtotal', 0)):.2f}",
        tax_rate=f"{float(invoice.get('tax_rate', 0)):.1f}",
        tax_amount=f"{float(invoice.get('tax_amount', 0)):.2f}",
        total=f"{float(invoice.get('total', 0)):.2f}",
        notes=escape(invoice.get("notes") or "").replace("\n", "<br>"),
        payment_terms=escape(profile.get("payment_terms") or ""),
    )


# ─── Stdlib fallback ─────────────────────────────────────────────────────


def _render_fallback_pdf(invoice: dict[str, Any], profile: dict[str, Any], client: dict[str, Any] | None) -> bytes:
    """Minimal valid PDF — single page, monospaced text dump."""
    lines = _plain_text_dump(invoice, profile, client)
    stream_lines: list[str] = ["BT", "/F1 11 Tf", "1 0 0 1 50 770 Tm", "14 TL"]
    for line in lines[:60]:
        stream_lines.append(f"({_pdf_escape(line)}) Tj T*")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines).encode("latin-1", errors="replace")

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    add(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
    add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    body = bytearray()
    offsets: list[int] = []
    body.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    for idx, payload in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{idx} 0 obj\n".encode("ascii"))
        body.extend(payload)
        body.extend(b"\nendobj\n")
    xref_offset = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    body.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(body)


def _plain_text_dump(invoice: dict[str, Any], profile: dict[str, Any], client: dict[str, Any] | None) -> list[str]:
    out: list[str] = [
        f"INVOICE {invoice.get('invoice_number', '')}",
        f"Issued: {invoice.get('issued_date', '')}    Due: {invoice.get('due_date', '')}",
        "",
        f"From: {profile.get('name', '')}  {profile.get('company') or ''}",
        f"      {profile.get('email', '')}",
        f"      Tax ID: {profile.get('tax_id') or '-'}",
        "",
        f"Bill to: {(client or {}).get('name', '-')}",
        f"         {(client or {}).get('email', '')}",
        "",
        "-" * 72,
        f"{'Description':<40}{'Hours':>8}{'Rate':>10}{'Amount':>14}",
        "-" * 72,
    ]
    for item in invoice.get("line_items", []):
        out.append(
            f"{str(item.get('description', ''))[:40]:<40}"
            f"{float(item.get('hours', 0)):>8.2f}"
            f"{float(item.get('rate', 0)):>10.2f}"
            f"{float(item.get('amount', 0)):>14.2f}"
        )
    currency = invoice.get("currency") or "USD"
    tax_rate = float(invoice.get("tax_rate", 0))
    out.extend(
        [
            "-" * 72,
            f"{'Subtotal':>62}{float(invoice.get('subtotal', 0)):>10.2f}",
            f"{f'Tax ({tax_rate:.1f}%)':>62}{float(invoice.get('tax_amount', 0)):>10.2f}",
            f"{'Total ' + currency:>62}{float(invoice.get('total', 0)):>10.2f}",
        ]
    )
    if profile.get("iban"):
        out.append("")
        out.append(f"IBAN: {profile.get('iban')}")
        if profile.get("bank_name"):
            out.append(f"Bank: {profile.get('bank_name')}")
    return out


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
