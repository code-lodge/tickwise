"""Thin wrapper over the Cloudflare API needed for tunnel setup.

We only call the few endpoints needed by the 4-step setup wizard:

- ``GET /accounts``  → account id
- ``GET /zones``     → list domains under the account
- ``POST /accounts/{id}/cfd_tunnel`` → create the named tunnel + secret
- ``PUT /accounts/{id}/cfd_tunnel/{tid}/configurations`` → ingress rules
- ``POST /zones/{zid}/dns_records`` → create the CNAME

httpx is the only dependency; the calling code is responsible for
storing and reading the API token from the keyring.
"""

from __future__ import annotations

import base64
import logging
import secrets
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareAPIError(RuntimeError):
    """Raised when Cloudflare returns a non-success payload."""


@dataclass(slots=True)
class CloudflareAPIClient:
    """Stateful wrapper bound to one API token."""

    api_token: str
    http: httpx.Client | None = None

    # ─── account / zone discovery ────────────────────────────────────────

    def list_accounts(self) -> list[dict[str, Any]]:
        return self._get("/accounts")["result"] or []

    def list_zones(self, account_id: str | None = None) -> list[dict[str, Any]]:
        params = {"account.id": account_id} if account_id else {}
        return self._get("/zones", params=params)["result"] or []

    # ─── tunnel lifecycle ───────────────────────────────────────────────

    def create_tunnel(self, account_id: str, name: str) -> dict[str, Any]:
        """Create a named tunnel; returns the tunnel object incl. credentials."""
        body = {
            "name": name,
            "tunnel_secret": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
            "config_src": "cloudflare",
        }
        result = self._post(f"/accounts/{account_id}/cfd_tunnel", body)["result"]
        return dict(result)

    def delete_tunnel(self, account_id: str, tunnel_id: str) -> None:
        self._delete(f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}")

    def configure_tunnel(self, account_id: str, tunnel_id: str, hostname: str, service: str) -> dict[str, Any]:
        """Apply the standard Tickwise ingress rules to a tunnel."""
        body = {
            "config": {
                "ingress": [
                    {
                        "hostname": hostname,
                        "path": "api/calendar/feed/.*",
                        "service": service,
                    },
                    {
                        "hostname": hostname,
                        "path": "api/mobile/.*",
                        "service": service,
                    },
                    {"service": "http_status:404"},
                ]
            }
        }
        result = self._put(f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations", body)["result"]
        return dict(result)

    # ─── DNS ────────────────────────────────────────────────────────────

    def create_cname(self, zone_id: str, hostname: str, target: str) -> dict[str, Any]:
        body = {
            "type": "CNAME",
            "name": hostname,
            "content": target,
            "proxied": True,
            "ttl": 1,
        }
        result = self._post(f"/zones/{zone_id}/dns_records", body)["result"]
        return dict(result)

    def delete_dns_record(self, zone_id: str, record_id: str) -> None:
        self._delete(f"/zones/{zone_id}/dns_records/{record_id}")

    # ─── transport ──────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, json=body)

    def _put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self._request("PUT", path, json=body)

    def _delete(self, path: str) -> dict[str, Any]:
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, **kw: Any) -> dict[str, Any]:
        url = _API_BASE + path
        try:
            if self.http is not None:
                response = self.http.request(method, url, headers=self._headers(), **kw)
            else:
                with httpx.Client(timeout=15.0) as client:
                    response = client.request(method, url, headers=self._headers(), **kw)
        except httpx.HTTPError as exc:
            raise CloudflareAPIError(f"transport: {exc}") from exc
        if response.status_code >= 400:
            raise CloudflareAPIError(f"{method} {path} failed: HTTP {response.status_code} {response.text[:200]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise CloudflareAPIError(f"non-JSON response from {path}") from exc
        if not payload.get("success", False):
            errors = payload.get("errors") or []
            raise CloudflareAPIError(f"{method} {path}: {errors}")
        return dict(payload)
