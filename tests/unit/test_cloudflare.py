"""Unit tests for the Cloudflare integration (binary, API client, manager)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from chronolens.cloudflare import binary as binary_mod
from chronolens.cloudflare import setup as setup_mod
from chronolens.cloudflare.api_client import CloudflareAPIClient, CloudflareAPIError
from chronolens.cloudflare.tunnel_manager import TunnelManager
from chronolens.crypto import keyring


def _success(payload: dict) -> dict:
    return {"success": True, "result": payload, "errors": []}


def _make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.unit
class TestCloudflareAPIClient:
    def test_list_accounts(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.headers["Authorization"] == "Bearer tok"
            return httpx.Response(200, json=_success([{"id": "acct-1", "name": "x"}]))

        client = CloudflareAPIClient(api_token="tok", http=_make_client(handler))
        accounts = client.list_accounts()
        assert accounts == [{"id": "acct-1", "name": "x"}]

    def test_create_tunnel_returns_result(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            assert req.method == "POST"
            return httpx.Response(200, json=_success({"id": "tun-1", "token": "T"}))

        client = CloudflareAPIClient(api_token="tok", http=_make_client(handler))
        result = client.create_tunnel("acct-1", "chronolens")
        assert result["id"] == "tun-1"

    def test_failure_response_raises(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"success": False, "errors": [{"message": "invalid"}]})

        client = CloudflareAPIClient(api_token="tok", http=_make_client(handler))
        with pytest.raises(CloudflareAPIError):
            client.list_zones()

    def test_transport_error_wrapped(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline")

        client = CloudflareAPIClient(api_token="tok", http=_make_client(handler))
        with pytest.raises(CloudflareAPIError):
            client.list_accounts()


@pytest.mark.unit
class TestSetupWizard:
    def test_store_token_persists_when_validated(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()

        client = _make_client(lambda req: httpx.Response(200, json=_success([{"id": "acct-1", "name": "Acme"}])))
        account = setup_mod.store_token("tok-12345", http_client=client)
        assert account["id"] == "acct-1"
        assert keyring.retrieve("cloudflare_api_token") == "tok-12345"

    def test_activate_writes_state(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmp_db: Path) -> None:
        monkeypatch.setattr(keyring, "_get_keyring", lambda: None)
        monkeypatch.setattr(keyring, "data_dir", lambda: tmp_path)
        keyring._reset_for_test()
        keyring.store("cloudflare_api_token", "tok")

        responses = iter(
            [
                _success({"id": "tun-1", "token": "TUNNEL-TOK"}),
                _success({"applied": True}),
                _success({"id": "rec-1"}),
            ]
        )

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=next(responses))

        state = setup_mod.activate(
            "acct-1",
            "zone-1",
            "time.example.com",
            http_client=_make_client(handler),
        )
        assert state.is_active is True
        assert state.tunnel_id == "tun-1"
        assert state.hostname == "time.example.com"
        assert keyring.retrieve("cloudflare_tunnel_token") == "TUNNEL-TOK"


@pytest.mark.unit
class TestBinary:
    def test_target_is_platform_specific(self) -> None:
        target = binary_mod._binary_target()
        assert target.local_filename in {"cloudflared", "cloudflared.exe"}
        assert target.url.startswith("https://github.com/cloudflare/cloudflared/releases/")

    def test_ensure_binary_downloads(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # Force a non-tgz target so we don't go through the archive path.
        monkeypatch.setattr(
            binary_mod,
            "_binary_target",
            lambda: binary_mod.BinaryTarget("cloudflared-linux-amd64", "cloudflared"),
        )
        monkeypatch.setattr(binary_mod, "data_dir", lambda: tmp_path)

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"fake-binary")

        path = binary_mod.ensure_binary(http=_make_client(handler))
        assert path.exists()
        assert path.read_bytes() == b"fake-binary"

    def test_ensure_binary_failure_raises(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(
            binary_mod,
            "_binary_target",
            lambda: binary_mod.BinaryTarget("cloudflared-linux-amd64", "cloudflared"),
        )
        monkeypatch.setattr(binary_mod, "data_dir", lambda: tmp_path)

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(404, content=b"")

        with pytest.raises(RuntimeError):
            binary_mod.ensure_binary(http=_make_client(handler))


@pytest.mark.unit
class TestTunnelManager:
    def test_start_marks_running_when_subprocess_alive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from chronolens.cloudflare import tunnel_manager as tm

        proc = MagicMock()
        proc.poll.return_value = None  # still running
        proc.pid = 4242
        proc.stdout = None
        monkeypatch.setattr(tm.subprocess, "Popen", lambda *a, **kw: proc)

        manager = TunnelManager()
        status = manager.start("token-x", binary=Path("/tmp/cloudflared"))
        assert status.running is True
        assert status.pid == 4242
        manager.stop()

    def test_start_failure_records_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from chronolens.cloudflare import tunnel_manager as tm

        def boom(*a: object, **kw: object) -> object:
            raise OSError("missing")

        monkeypatch.setattr(tm.subprocess, "Popen", boom)
        manager = TunnelManager()
        status = manager.start("token-x", binary=Path("/nope"))
        assert status.running is False
        assert "missing" in (status.last_error or "")

    def test_status_when_never_started(self) -> None:
        manager = TunnelManager()
        status = manager.status()
        assert status.running is False
        assert status.pid is None
