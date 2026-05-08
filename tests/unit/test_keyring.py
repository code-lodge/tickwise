"""Unit tests for tickwise.crypto.keyring (file fallback path)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tickwise.crypto import keyring as kr


@pytest.fixture(autouse=True)
def _isolate_keyring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the file fallback by hiding the `keyring` library, and
    redirect the secrets file into a temp dir for each test."""
    monkeypatch.setattr(kr, "_get_keyring", lambda: None)
    monkeypatch.setattr(kr, "data_dir", lambda: tmp_path)
    kr._reset_for_test()


@pytest.mark.unit
class TestFileFallback:
    def test_round_trip(self) -> None:
        kr.store("anthropic_api_key", "sk-test-secret")
        assert kr.retrieve("anthropic_api_key") == "sk-test-secret"

    def test_overwrite(self) -> None:
        kr.store("k", "v1")
        kr.store("k", "v2")
        assert kr.retrieve("k") == "v2"

    def test_missing_key_returns_none(self) -> None:
        assert kr.retrieve("nope") is None

    def test_delete(self) -> None:
        kr.store("k", "v")
        kr.delete("k")
        assert kr.retrieve("k") is None

    def test_delete_missing_is_noop(self) -> None:
        kr.delete("never-set")  # must not raise

    def test_empty_key_rejected(self) -> None:
        with pytest.raises(ValueError):
            kr.store("", "v")
        with pytest.raises(ValueError):
            kr.retrieve("")
        with pytest.raises(ValueError):
            kr.delete("")

    def test_ciphertext_is_not_plaintext(self, tmp_path: Path) -> None:
        kr.store("k", "very-secret-value")
        body = (tmp_path / "secrets.json").read_text("utf-8")
        assert "very-secret-value" not in body
        assert "k" in body  # the alias, not the value

    def test_tampered_ciphertext_returns_none(self) -> None:
        kr.store("k", "v")
        # Mutate the file: replace the stored token with garbage.
        path = kr._secrets_path()
        path.write_text('{"k": "AAAAAAAAAAAAAAAAAAAAAAAA"}', encoding="utf-8")
        assert kr.retrieve("k") is None


@pytest.mark.unit
class TestKeyringBackend:
    def test_uses_real_keyring_when_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = MagicMock()
        fake.get_password.return_value = "stored-via-os"
        monkeypatch.setattr(kr, "_get_keyring", lambda: fake)
        kr.store("api", "v")
        fake.set_password.assert_called_once_with(kr._KEYRING_SERVICE, "api", "v")

        assert kr.retrieve("api") == "stored-via-os"
        fake.get_password.assert_called_with(kr._KEYRING_SERVICE, "api")

        kr.delete("api")
        fake.delete_password.assert_called_with(kr._KEYRING_SERVICE, "api")

    def test_falls_back_to_file_when_keyring_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = MagicMock()
        fake.get_password.return_value = None
        monkeypatch.setattr(kr, "_get_keyring", lambda: fake)
        # Pre-seed the file fallback with a value.
        kr._file_store("orphan", "v-from-file")
        assert kr.retrieve("orphan") == "v-from-file"
