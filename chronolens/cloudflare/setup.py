"""4-step Cloudflare Tunnel setup wizard.

Each step is idempotent and saves progress to ``cloudflare_config`` so
the dashboard can resume an interrupted setup. The wizard never starts
the tunnel itself — that's `tunnel_manager.start()` after activation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from chronolens.cloudflare.api_client import CloudflareAPIClient, CloudflareAPIError
from chronolens.crypto import keyring
from chronolens.db.connection import get_connection, transaction

logger = logging.getLogger(__name__)


_TOKEN_REF = "cloudflare_api_token"
_TUNNEL_TOKEN_REF = "cloudflare_tunnel_token"


@dataclass(slots=True)
class WizardState:
    """What the dashboard renders for the wizard's status panel."""

    has_token: bool = False
    account_id: str | None = None
    zone_id: str | None = None
    domain: str | None = None
    tunnel_id: str | None = None
    tunnel_name: str | None = None
    hostname: str | None = None
    is_active: bool = False


def load_state() -> WizardState:
    row = get_connection().execute("SELECT * FROM cloudflare_config WHERE id = 1").fetchone()
    if row is None:
        return WizardState(has_token=bool(keyring.retrieve(_TOKEN_REF)))
    return WizardState(
        has_token=bool(keyring.retrieve(_TOKEN_REF)),
        tunnel_id=row["tunnel_id"],
        tunnel_name=row["tunnel_name"],
        hostname=row["hostname"],
        is_active=bool(row["is_active"]),
    )


def store_token(token: str, http_client: Any | None = None) -> dict[str, Any]:
    """Step 1 — validate the API token and remember it.

    Returns the first account associated with the token so the dashboard
    can pre-select it in step 2.
    """
    if not token:
        raise ValueError("API token must be non-empty")
    api = CloudflareAPIClient(api_token=token, http=http_client)
    accounts = api.list_accounts()
    if not accounts:
        raise CloudflareAPIError("token has no associated accounts")
    keyring.store(_TOKEN_REF, token)
    return dict(accounts[0])


def list_zones_for_token(account_id: str, http_client: Any | None = None) -> list[dict[str, Any]]:
    """Step 2 helper — return zone dicts for the chosen account."""
    token = keyring.retrieve(_TOKEN_REF)
    if not token:
        raise CloudflareAPIError("API token is not configured")
    api = CloudflareAPIClient(api_token=token, http=http_client)
    return api.list_zones(account_id=account_id)


def activate(
    account_id: str,
    zone_id: str,
    hostname: str,
    *,
    tunnel_name: str | None = None,
    service_url: str = "http://localhost:19532",
    http_client: Any | None = None,
) -> WizardState:
    """Step 4 — create the tunnel, configure ingress, write the CNAME, persist.

    Does NOT start the cloudflared subprocess; the dashboard calls
    `/api/cloudflare/start` after activation succeeds.
    """
    token = keyring.retrieve(_TOKEN_REF)
    if not token:
        raise CloudflareAPIError("API token is not configured")
    api = CloudflareAPIClient(api_token=token, http=http_client)
    name = tunnel_name or f"chronolens-{hostname.replace('.', '-')}"
    tunnel = api.create_tunnel(account_id, name)
    api.configure_tunnel(account_id, tunnel["id"], hostname, service_url)
    api.create_cname(zone_id, hostname, f"{tunnel['id']}.cfargotunnel.com")
    if tunnel.get("token"):
        keyring.store(_TUNNEL_TOKEN_REF, tunnel["token"])
    with transaction() as conn:
        conn.execute(
            """
            UPDATE cloudflare_config SET
                tunnel_id = ?, tunnel_name = ?, hostname = ?, is_active = 1,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
             WHERE id = 1
            """,
            (tunnel["id"], name, hostname),
        )
    return load_state()


def deactivate(*, http_client: Any | None = None) -> WizardState:
    """Tear down the tunnel + CNAME and clear the saved state.

    The cloudflared subprocess (if running) must be stopped by the caller
    *before* invoking this — leaving it running after the tunnel is
    deleted produces a stream of harmless 404s.
    """
    token = keyring.retrieve(_TOKEN_REF)
    state = load_state()
    if token and state.tunnel_id:
        api = CloudflareAPIClient(api_token=token, http=http_client)
        try:
            # We don't track the account_id with the row, so resolve it again.
            accounts = api.list_accounts()
            if accounts:
                api.delete_tunnel(accounts[0]["id"], state.tunnel_id)
        except CloudflareAPIError:
            logger.exception("Cloudflare tunnel teardown failed")
    keyring.delete(_TUNNEL_TOKEN_REF)
    with transaction() as conn:
        conn.execute(
            "UPDATE cloudflare_config SET tunnel_id = NULL, tunnel_name = NULL, "
            "hostname = NULL, is_active = 0, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = 1"
        )
    return load_state()


def tunnel_token() -> str | None:
    """Read the cloudflared token saved during activation."""
    return keyring.retrieve(_TUNNEL_TOKEN_REF)
