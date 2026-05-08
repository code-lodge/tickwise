"""PDF rendering for reports.

Uses WeasyPrint when available — its dependency footprint is significant
(GTK, Pango), so we fall back to a tiny self-contained PDF emitted by
hand for environments where WeasyPrint isn't installed (CI, slim
container builds). The fallback isn't pretty but produces a valid
single-page document the caller can ship.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def to_pdf(report: dict[str, Any]) -> bytes:
    """Render the report dict to bytes — WeasyPrint preferred, fallback otherwise."""
    html = render_html(report)
    try:
        from weasyprint import HTML
    except ImportError:
        return _render_fallback_pdf(report)
    return bytes(HTML(string=html).write_pdf() or b"")


# ─── HTML template (also useful for the dashboard preview) ──────────────


def render_html(report: dict[str, Any]) -> str:
    rtype = report.get("type", "summary")
    title_map = {
        "summary": "Time Summary",
        "billing": "Billing Report",
        "activity": "Activity Breakdown",
        "detailed": "Detailed Log",
        "productivity": "Productivity Report",
    }
    title = title_map.get(str(rtype), "Report")
    body = _body_for_type(report)
    generated = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 2.5rem; color: #0f172a; }}
  h1 {{ margin: 0 0 0.5rem 0; }}
  .meta {{ color: #64748b; margin-bottom: 1.5rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }}
  th, td {{ text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #e2e8f0; }}
  th {{ background: #f8fafc; }}
  tfoot td {{ font-weight: 600; }}
</style></head>
<body>
  <h1>{title}</h1>
  <p class="meta">{report.get("from", "")} → {report.get("to", "")} · generated {generated}</p>
  {body}
</body></html>
"""


def _body_for_type(report: dict[str, Any]) -> str:
    rtype = report.get("type")
    if rtype == "summary":
        rows = "".join(
            f"<tr><td>{r['project']}</td><td>{r['seconds'] / 3600:.2f}</td></tr>" for r in report.get("by_project", [])
        )
        return f"<table><thead><tr><th>Project</th><th>Hours</th></tr></thead><tbody>{rows}</tbody></table>"
    if rtype == "billing":
        rows = "".join(
            f"<tr><td>{r['project']}</td>"
            f"<td>{r['billable_seconds'] / 3600:.2f}</td>"
            f"<td>{r['rate']}</td>"
            f"<td>{r['amount']:.2f} {r['currency']}</td></tr>"
            for r in report.get("by_project", [])
        )
        total = report.get("grand_total_amount", 0)
        return (
            "<table><thead><tr><th>Project</th><th>Billable hours</th><th>Rate</th><th>Amount</th></tr></thead>"
            f"<tbody>{rows}</tbody>"
            f"<tfoot><tr><td colspan='3'>Total</td><td>{total:.2f}</td></tr></tfoot></table>"
        )
    if rtype == "activity":
        rows = "".join(
            f"<tr><td>{r['category']}</td><td>{r['project']}</td>"
            f"<td>{r['seconds'] / 3600:.2f}</td><td>{r['sessions']}</td></tr>"
            for r in report.get("rows", [])
        )
        return (
            "<table><thead><tr><th>Category</th><th>Project</th><th>Hours</th><th>Sessions</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    if rtype == "detailed":
        rows = "".join(
            f"<tr><td>{r['started_at']}</td><td>{r['ended_at'] or ''}</td>"
            f"<td>{r['duration_secs'] / 3600:.2f}</td>"
            f"<td>{r['project'] or ''}</td><td>{(r['description'] or '').replace('<', '&lt;')}</td></tr>"
            for r in report.get("sessions", [])
        )
        return (
            "<table><thead><tr><th>Started</th><th>Ended</th><th>Hours</th><th>Project</th><th>Description</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    if rtype == "productivity":
        rows = "".join(
            f"<tr><td>{r['hour']:02d}:00</td><td>{r['seconds'] / 3600:.2f}</td></tr>"
            for r in report.get("active_by_hour", [])
        )
        return "<table><thead><tr><th>Hour</th><th>Active hours</th></tr></thead>" f"<tbody>{rows}</tbody></table>"
    return "<p>Empty report.</p>"


# ─── pure-stdlib fallback ───────────────────────────────────────────────


def _render_fallback_pdf(report: dict[str, Any]) -> bytes:
    """Hand-rolled minimal PDF — single page, monospace text dump.

    Good enough for tests and headless environments. Not suitable for
    the polished invoice in Phase 6 — that path requires WeasyPrint.
    """
    text = _plain_text_dump(report)
    lines = text.splitlines() or [""]
    # Build a content stream with one Tj per line.
    stream_lines: list[str] = ["BT", "/F1 11 Tf", "1 0 0 1 50 770 Tm", "14 TL"]
    for line in lines[:60]:  # one page, ~60 rows max
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


def _plain_text_dump(report: dict[str, Any]) -> str:
    rtype = str(report.get("type", "report")).upper()
    out = [f"ChronoLens — {rtype}", f"Range: {report.get('from')} → {report.get('to')}", ""]
    if report.get("type") == "summary":
        for row in report.get("by_project", []):
            out.append(f"{row['project']:<32}{row['seconds'] / 3600:>8.2f} h")
        out.append("")
        out.append(f"Total seconds: {report.get('total_seconds', 0)}")
    elif report.get("type") == "billing":
        for row in report.get("by_project", []):
            out.append(
                f"{row['project']:<28}{row['billable_seconds'] / 3600:>6.2f}h × {row['rate']:>6} = {row['amount']:>10.2f} {row['currency']}"
            )
        out.append(f"Total: {report.get('grand_total_amount', 0):.2f}")
    elif report.get("type") == "detailed":
        for row in report.get("sessions", []):
            out.append(
                f"{row['started_at']}  {row['duration_secs'] / 3600:>6.2f}h  "
                f"{(row['project'] or '-'):<20}{row['description'] or ''}"
            )
    return "\n".join(out)


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
