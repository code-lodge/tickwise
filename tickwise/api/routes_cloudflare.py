"""Cloudflare Tunnel setup-wizard endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tickwise.cloudflare.api_client import CloudflareAPIError
from tickwise.cloudflare.binary import (
    binary_path,
    ensure_binary,
    is_installed,
)
from tickwise.cloudflare.setup import (
    activate,
    deactivate,
    list_zones_for_token,
    load_state,
    store_token,
    tunnel_token,
)
from tickwise.cloudflare.tunnel_manager import cloudflared_available, get_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cloudflare", tags=["cloudflare"])


class TokenPayload(BaseModel):
    api_token: str = Field(min_length=20)


class ActivatePayload(BaseModel):
    account_id: str = Field(min_length=1)
    zone_id: str = Field(min_length=1)
    hostname: str = Field(min_length=1, max_length=253)
    tunnel_name: str | None = None
    service_url: str = "http://localhost:19532"


@router.get("/state", response_model=dict[str, Any])
async def get_state() -> dict[str, Any]:
    state = load_state()
    manager_status = get_manager().status()
    return {
        "has_token": state.has_token,
        "tunnel_id": state.tunnel_id,
        "tunnel_name": state.tunnel_name,
        "hostname": state.hostname,
        "is_active": state.is_active,
        "binary_installed": is_installed(),
        "binary_available": cloudflared_available(),
        "tunnel_running": manager_status.running,
        "last_log_line": manager_status.last_log_line,
        "last_error": manager_status.last_error,
    }


@router.post("/token", response_model=dict[str, Any])
async def save_token(payload: TokenPayload) -> dict[str, Any]:
    try:
        account = store_token(payload.api_token)
    except CloudflareAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"account": account, "state": (await get_state())}


@router.get("/zones", response_model=list[dict[str, Any]])
async def list_zones(account_id: str) -> list[dict[str, Any]]:
    try:
        return list_zones_for_token(account_id)
    except CloudflareAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/activate", response_model=dict[str, Any])
async def activate_tunnel(payload: ActivatePayload) -> dict[str, Any]:
    try:
        state = activate(
            payload.account_id,
            payload.zone_id,
            payload.hostname,
            tunnel_name=payload.tunnel_name,
            service_url=payload.service_url,
        )
    except CloudflareAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"state": state.__dict__}


@router.post("/deactivate", response_model=dict[str, Any])
async def deactivate_tunnel() -> dict[str, Any]:
    get_manager().stop()
    state = deactivate()
    return {"state": state.__dict__}


@router.post("/binary/download", response_model=dict[str, Any])
async def install_binary() -> dict[str, Any]:
    try:
        path = ensure_binary()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"path": str(path), "installed": is_installed()}


@router.post("/start", response_model=dict[str, Any])
async def start_tunnel() -> dict[str, Any]:
    token = tunnel_token()
    if not token:
        raise HTTPException(status_code=400, detail="Tunnel not yet activated")
    if not is_installed():
        raise HTTPException(status_code=400, detail="cloudflared binary missing — call /binary/download first")
    status = get_manager().start(token, binary=binary_path())
    return status.__dict__


@router.post("/stop", response_model=dict[str, Any])
async def stop_tunnel() -> dict[str, Any]:
    get_manager().stop()
    return get_manager().status().__dict__
