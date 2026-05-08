"""Freelancer profile + logo upload endpoints."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from tickwise.db.connection import get_connection, transaction
from tickwise.platform.paths import data_dir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])

_ALLOWED_LOGO_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
_MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


class FreelancerProfile(BaseModel):
    name: str = ""
    email: str = ""
    company: str | None = None
    address: str | None = None
    tax_id: str | None = None
    iban: str | None = None
    bank_name: str | None = None
    payment_terms: str | None = None
    default_currency: str = "USD"
    default_hourly_rate: float | None = None
    timezone: str = "UTC"
    invoice_prefix: str = Field(default="INV", min_length=1, max_length=8)
    invoice_next_number: int = Field(default=1, ge=1)
    invoice_default_due_days: int = Field(default=14, ge=0, le=365)
    invoice_default_tax_rate: float = Field(default=21.0, ge=0, le=100)
    logo_path: str | None = None


@router.get("", response_model=FreelancerProfile)
async def get_profile() -> FreelancerProfile:
    row = get_connection().execute("SELECT * FROM freelancer_profile WHERE id = 1").fetchone()
    if row is None:
        return FreelancerProfile()
    keys = row.keys()
    payload = {k: row[k] for k in FreelancerProfile.model_fields if k in keys}
    return FreelancerProfile(**payload)


@router.put("", response_model=FreelancerProfile)
async def update_profile(payload: FreelancerProfile) -> FreelancerProfile:
    with transaction() as conn:
        conn.execute(
            """
            UPDATE freelancer_profile SET
                name = ?, email = ?, company = ?, address = ?, tax_id = ?,
                iban = ?, bank_name = ?, payment_terms = ?,
                default_currency = ?, default_hourly_rate = ?, timezone = ?,
                invoice_prefix = ?, invoice_next_number = ?,
                invoice_default_due_days = ?, invoice_default_tax_rate = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE id = 1
            """,
            (
                payload.name,
                payload.email,
                payload.company,
                payload.address,
                payload.tax_id,
                payload.iban,
                payload.bank_name,
                payload.payment_terms,
                payload.default_currency,
                payload.default_hourly_rate,
                payload.timezone,
                payload.invoice_prefix,
                payload.invoice_next_number,
                payload.invoice_default_due_days,
                payload.invoice_default_tax_rate,
            ),
        )
    return await get_profile()


_logo_field = File(...)


@router.post("/logo")
async def upload_logo(file: UploadFile = _logo_field) -> dict[str, str]:
    if file.content_type not in _ALLOWED_LOGO_TYPES:
        raise HTTPException(status_code=415, detail=f"unsupported logo type: {file.content_type}")
    payload = await file.read()
    if len(payload) > _MAX_LOGO_BYTES:
        raise HTTPException(status_code=413, detail="logo exceeds 2 MB")

    suffix = Path(file.filename or "logo").suffix or ".png"
    target_dir = data_dir() / "logos"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"logo-{uuid.uuid4().hex}{suffix}"
    target.write_bytes(payload)

    with transaction() as conn:
        conn.execute(
            "UPDATE freelancer_profile SET logo_path = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = 1",
            (str(target),),
        )
    return {"logo_path": str(target)}
