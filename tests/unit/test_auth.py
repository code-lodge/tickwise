"""Unit tests for the bearer-token auth helpers."""

from __future__ import annotations

import pytest

from chronolens.api import auth
from chronolens.db.connection import transaction


@pytest.mark.unit
class TestIssueAndList:
    def test_issue_returns_unique_token(self, tmp_db) -> None:
        a, _ = auth.issue_token("phone")
        b, _ = auth.issue_token("tablet")
        assert a != b
        assert len(a) == 64

    def test_list_tokens_orders_newest_first(self, tmp_db) -> None:
        auth.issue_token("first")
        auth.issue_token("second")
        rows = auth.list_tokens()
        assert [r.device_name for r in rows] == ["second", "first"]

    def test_revoke_removes(self, tmp_db) -> None:
        _, tid = auth.issue_token("x")
        assert auth.revoke_token(tid) is True
        assert auth.list_tokens() == []
        assert auth.revoke_token(tid) is False


@pytest.mark.unit
class TestRequireBearerToken:
    @pytest.mark.asyncio
    async def test_missing_header_rejected(self, tmp_db) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as ei:
            await auth.require_bearer_token(authorization=None)
        assert ei.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_scheme_rejected(self, tmp_db) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as ei:
            await auth.require_bearer_token(authorization="Basic abc")
        assert ei.value.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_token_rejected(self, tmp_db) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as ei:
            await auth.require_bearer_token(authorization="Bearer deadbeef")
        assert ei.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_passes_and_updates_last_used(self, tmp_db) -> None:
        token, tid = auth.issue_token("phone")
        info = await auth.require_bearer_token(authorization=f"Bearer {token}")
        assert info.id == tid
        # last_used should now be populated
        rows = auth.list_tokens()
        assert rows[0].last_used is not None

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, tmp_db) -> None:
        from fastapi import HTTPException

        token, tid = auth.issue_token("phone")
        with transaction() as conn:
            conn.execute(
                "UPDATE mobile_auth_tokens SET expires_at = '2020-01-01T00:00:00+00:00' WHERE id = ?",
                (tid,),
            )
        with pytest.raises(HTTPException) as ei:
            await auth.require_bearer_token(authorization=f"Bearer {token}")
        assert ei.value.status_code == 401
