"""Dashboard-side pairing endpoints — issue + revoke mobile tokens.

These endpoints are *not* bearer-authenticated because they're served
on the localhost-only dashboard. Cloudflare Tunnel ingress restricts
public exposure to /api/calendar/feed/* and /api/mobile/*, so these
admin endpoints stay loopback-only by design.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from chronolens.api import auth
from chronolens.db.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pairing", tags=["pairing"])


class PairRequest(BaseModel):
    device_name: str | None = Field(default=None, max_length=120)
    ttl_days: int | None = Field(default=None, ge=1, le=3650)
    base_url: str | None = Field(default=None)


class PairResponse(BaseModel):
    token_id: int
    token: str
    pairing_url: str
    qr_svg: str


def _qr_svg(payload: str) -> str:
    """Render a QR payload as inline SVG so the dashboard can drop it into the DOM."""
    import qrcode
    from qrcode.image.svg import SvgPathImage

    img = qrcode.make(payload, image_factory=SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


@router.post("/start", response_model=PairResponse)
async def start_pairing(payload: PairRequest) -> PairResponse:
    base = (payload.base_url or "").rstrip("/")
    if not base:
        cf = get_connection().execute("SELECT hostname, is_active FROM cloudflare_config WHERE id = 1").fetchone()
        base = (
            f"https://{cf['hostname']}"
            if cf and cf["is_active"] and cf["hostname"]
            else "http://127.0.0.1:19532"
        )
    token, token_id = auth.issue_token(payload.device_name, ttl_days=payload.ttl_days)
    pairing_url = f"{base}/m/?t={token}"
    return PairResponse(
        token_id=token_id,
        token=token,
        pairing_url=pairing_url,
        qr_svg=_qr_svg(pairing_url),
    )


@router.get("/tokens")
async def list_paired_devices() -> list[dict[str, Any]]:
    return [
        {
            "id": t.id,
            "device_name": t.device_name,
            "created_at": t.created_at,
            "last_used": t.last_used,
            "expires_at": t.expires_at,
        }
        for t in auth.list_tokens()
    ]


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_paired_device(token_id: int) -> None:
    if not auth.revoke_token(token_id):
        raise HTTPException(status_code=404, detail=f"token {token_id} not found")
