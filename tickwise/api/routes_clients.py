"""Clients CRUD — referenced by projects in the dashboard."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tickwise.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clients", tags=["clients"])


class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str | None = None
    timezone: str = "UTC"
    address: str | None = None
    tax_id: str | None = None


class ClientOut(ClientIn):
    id: int


def _row(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": int(data["id"]),
        "name": data["name"],
        "email": data.get("email"),
        "timezone": data["timezone"],
        "address": data.get("address"),
        "tax_id": data.get("tax_id"),
    }


@router.get("", response_model=list[ClientOut])
async def list_clients() -> list[ClientOut]:
    rows = get_connection().execute("SELECT * FROM clients ORDER BY name").fetchall()
    return [ClientOut(**_row(row)) for row in rows]


@router.post("", response_model=ClientOut, status_code=201)
async def create_client(payload: ClientIn) -> ClientOut:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO clients (name, email, timezone, address, tax_id) VALUES (?, ?, ?, ?, ?)",
            (payload.name, payload.email, payload.timezone, payload.address, payload.tax_id),
        )
        client_id = int(cur.lastrowid or 0)
    return ClientOut(id=client_id, **payload.model_dump())


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(client_id: int, payload: ClientIn) -> ClientOut:
    with transaction() as conn:
        cur = conn.execute(
            """
            UPDATE clients SET name = ?, email = ?, timezone = ?, address = ?, tax_id = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE id = ?
            """,
            (payload.name, payload.email, payload.timezone, payload.address, payload.tax_id, client_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return ClientOut(id=client_id, **payload.model_dump())


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: int) -> None:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
