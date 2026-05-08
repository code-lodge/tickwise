"""Bearer-token authentication for /api/mobile/*.

Tokens are 64-character hex strings. We never store the plaintext —
only `sha256(token)` lives in the `mobile_auth_tokens` row. On every
authenticated request the middleware hashes the presented token and
looks it up; mismatch → 401.

`issue_token()` generates a fresh token, persists its hash, and
returns the plaintext exactly once so the caller can render it into a
QR code.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Header, HTTPException, status

from tickwise.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TokenInfo:
    id: int
    token_hash: str
    device_name: str | None
    last_used: str | None
    expires_at: str | None
    created_at: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(device_name: str | None = None, *, ttl_days: int | None = None) -> tuple[str, int]:
    """Generate a fresh bearer token and persist its hash. Returns (token, row_id)."""
    token = secrets.token_hex(32)
    token_hash = _hash_token(token)
    expires_at: str | None = None
    if ttl_days is not None:
        expires_at = (datetime.now(tz=UTC) + timedelta(days=ttl_days)).isoformat()
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO mobile_auth_tokens (token_hash, device_name, expires_at) VALUES (?, ?, ?)",
            (token_hash, device_name, expires_at),
        )
        return token, int(cur.lastrowid or 0)


def list_tokens() -> list[TokenInfo]:
    rows = (
        get_connection()
        .execute(
            "SELECT id, token_hash, device_name, last_used, expires_at, created_at "
            "FROM mobile_auth_tokens ORDER BY id DESC"
        )
        .fetchall()
    )
    return [
        TokenInfo(
            id=int(r["id"]),
            token_hash=r["token_hash"],
            device_name=r["device_name"],
            last_used=r["last_used"],
            expires_at=r["expires_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


def revoke_token(token_id: int) -> bool:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM mobile_auth_tokens WHERE id = ?", (token_id,))
        return cur.rowcount > 0


def _is_expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        return datetime.fromisoformat(expires_at) < datetime.now(tz=UTC)
    except ValueError:
        return False


async def require_bearer_token(authorization: str | None = Header(default=None)) -> TokenInfo:
    """FastAPI dependency — validates the Authorization header.

    Accepts ``Authorization: Bearer <token>``. Updates ``last_used`` on
    success so admins can spot dead devices.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="empty bearer token")
    token_hash = _hash_token(token)
    row = (
        get_connection()
        .execute(
            "SELECT id, token_hash, device_name, last_used, expires_at, created_at "
            "FROM mobile_auth_tokens WHERE token_hash = ?",
            (token_hash,),
        )
        .fetchone()
    )
    if row is None:
        raise HTTPException(status_code=401, detail="invalid token")
    if _is_expired(row["expires_at"]):
        raise HTTPException(status_code=401, detail="token expired")
    with transaction() as conn:
        conn.execute(
            "UPDATE mobile_auth_tokens SET last_used = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (int(row["id"]),),
        )
    return TokenInfo(
        id=int(row["id"]),
        token_hash=row["token_hash"],
        device_name=row["device_name"],
        last_used=row["last_used"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
    )
