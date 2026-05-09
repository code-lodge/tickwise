"""Security invariants — these tests gate every release.

Each one maps to an item in `docs/SECURITY.md`. If a test starts failing
the response is to fix the code, not the test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tickwise.config import API_HOST, API_PORT


@pytest.mark.integration
class TestNetworkBoundary:
    def test_api_binds_loopback(self) -> None:
        assert API_HOST == "127.0.0.1", "API must bind to loopback only"

    def test_api_port_in_user_range(self) -> None:
        assert 1024 <= API_PORT <= 65535


@pytest.mark.integration
class TestCloudflareIngress:
    def test_ingress_allowlist_excludes_admin_paths(self) -> None:
        from tickwise.cloudflare import api_client

        src = Path(api_client.__file__).read_text(encoding="utf-8")
        assert "api/calendar/feed/.*" in src
        assert "api/mobile/.*" in src
        # Spot-check that no admin path leaks
        for forbidden in ("api/llm", "api/redaction", "api/backup", "api/pairing"):
            assert forbidden not in src, f"Cloudflare ingress must not expose {forbidden}"


@pytest.mark.integration
class TestSecretMaterial:
    def test_mobile_token_length(self) -> None:
        from tickwise.api.auth import issue_token

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("tickwise.api.auth.transaction", _stub_transaction())
            token, _ = issue_token("test")
        assert len(token) == 64
        assert re.fullmatch(r"[0-9a-f]+", token)

    def test_ics_feed_token_length(self) -> None:
        from tickwise.calendar.ics_feed import generate_token

        token = generate_token()
        assert len(token) == 32
        assert re.fullmatch(r"[0-9a-f]+", token)


@pytest.mark.integration
class TestDataRetention:
    def test_capture_loop_does_not_write_screenshots(self) -> None:
        src = Path("tickwise/capture/loop.py").read_text(encoding="utf-8")
        # The screenshot bytes live on a Screenshot dataclass and never
        # touch the filesystem. Catch any accidental Path.write_bytes
        # against a screenshot.
        assert ".write_bytes(" not in src or "screenshot" not in src.lower()
        assert "open(" not in src or "screenshot" not in src.lower()

    def test_persisted_text_is_capped(self) -> None:
        """OCR text gets truncated before it ever reaches SQLite.

        Cap was raised from 200 → 1500 chars so retrospective
        keyword reclassification can find brand names that don't
        always land in the first paragraph of a screenshot. The
        invariant we still defend is that *some* finite cap exists
        — we don't store unbounded screen text.
        """
        src = Path("tickwise/capture/loop.py").read_text(encoding="utf-8")
        assert "ocr_text[:1500]" in src, "redacted_text must be truncated before persistence"


@pytest.mark.integration
class TestBackupExclusions:
    def test_backup_excludes_secrets(self) -> None:
        from tickwise.api.routes_backup import _EXPORTED_TABLES

        for forbidden in (
            "mobile_auth_tokens",
            "classification_cache",
            "llm_usage_log",
            "redaction_log",
            "activities",
        ):
            assert forbidden not in _EXPORTED_TABLES, f"backup must not include {forbidden} (PII or regenerable)"


# ─── Helpers ─────────────────────────────────────────────────────────


def _stub_transaction():
    """Return a context manager that yields a stub conn — issue_token only does INSERT."""
    from contextlib import contextmanager

    class _StubConn:
        def execute(self, *_a, **_k):
            class _C:
                lastrowid = 1

            return _C()

    @contextmanager
    def _txn():
        yield _StubConn()

    return _txn
