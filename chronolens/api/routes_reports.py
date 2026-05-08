"""Report generation + export endpoints."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from chronolens.calendar.ics_feed import build_calendar
from chronolens.reports.csv_export import to_csv
from chronolens.reports.generator import ReportRequest, generate
from chronolens.reports.pdf_export import to_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

ReportType = Literal["summary", "billing", "activity", "detailed", "productivity"]
GroupBy = Literal["day", "week", "month"]


class ReportPayload(BaseModel):
    type: ReportType = "summary"
    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")
    project_ids: list[int] = Field(default_factory=list)
    group_by: GroupBy = "day"

    model_config = {"populate_by_name": True}


class ExportPayload(ReportPayload):
    format: Literal["json", "csv", "pdf", "ics"] = "json"


@router.post("/generate", response_model=dict[str, Any])
async def generate_report(payload: ReportPayload) -> dict[str, Any]:
    request = ReportRequest(
        type=payload.type,
        from_date=payload.from_date,
        to_date=payload.to_date,
        project_ids=payload.project_ids,
        group_by=payload.group_by,
    )
    try:
        return generate(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/export")
async def export_report(payload: ExportPayload) -> Response:
    request = ReportRequest(
        type=payload.type,
        from_date=payload.from_date,
        to_date=payload.to_date,
        project_ids=payload.project_ids,
        group_by=payload.group_by,
    )
    try:
        report = generate(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    base = f"chronolens-{payload.type}-{payload.from_date}-{payload.to_date}"

    if payload.format == "json":
        return Response(
            content=json.dumps(report, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={base}.json"},
        )
    if payload.format == "csv":
        return Response(
            content=to_csv(report),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={base}.csv"},
        )
    if payload.format == "pdf":
        return Response(
            content=to_pdf(report),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={base}.pdf"},
        )
    if payload.format == "ics":
        if payload.type != "detailed":
            raise HTTPException(status_code=422, detail="ics export requires type=detailed")
        sessions = [
            {
                "id": row["id"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "description": row["description"],
                "project_name": row["project"],
            }
            for row in report.get("sessions", [])
        ]
        body = build_calendar(sessions, include_descriptions=True)
        return Response(
            content=body,
            media_type="text/calendar; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={base}.ics"},
        )
    raise HTTPException(status_code=422, detail=f"unsupported format: {payload.format}")
