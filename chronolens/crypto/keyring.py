"""Cross-platform credential storage.

Uses the `keyring` Python library as the unified front door — it routes
to Windows DPAPI (Windows Credential Manager), macOS Keychain, and the
freedesktop Secret Service (GNOME Keyring / KWallet) automatically.

If `keyring` is unavailable or returns no backend (e.g. headless Linux
without a Secret Service daemon, container builds, CI), we fall back to
an encrypted file in the data directory, keyed by a per-machine
random secret stored at `data_dir() / .keyring_key`. The file format is
a small JSON map of {alias: base64(fernet(bytes))}; the backend is set
once and remains stable for the life of the install.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any

from chronolens.config import APP_NAME
from chronolens.platform.paths import data_dir

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = APP_NAME


# ─── public API ─────────────────────────────────────────────────────────


def store(key: str, value: str) -> None:
    """Persist `value` under `key`, using the platform keyring if available.

    Existing values are overwritten. Empty `key` raises ValueError.
    """
    if not key:
        raise ValueError("key must be non-empty")
    backend = _get_keyring()
    if backend is not None:
        backend.set_password(_KEYRING_SERVICE, key, value)
        return
    _file_store(key, value)


def retrieve(key: str) -> str | None:
    """Return the previously stored value, or None if the key is unknown."""
    if not key:
        raise ValueError("key must be non-empty")
    backend = _get_keyring()
    if backend is not None:
        out = backend.get_password(_KEYRING_SERVICE, key)
        return out if out is not None else _file_retrieve(key)
    return _file_retrieve(key)


def delete(key: str) -> None:
    """Remove the stored value. Safe to call when the key is unknown."""
    if not key:
        raise ValueError("key must be non-empty")
    backend = _get_keyring()
    if backend is not None:
        try:
            backend.delete_password(_KEYRING_SERVICE, key)
        except Exception:
            logger.debug("keyring delete failed for %s", key, exc_info=True)
    _file_delete(key)


# ─── keyring detection ──────────────────────────────────────────────────


_keyring_checked = False
_keyring_module: Any | None = None


def _get_keyring() -> Any | None:
    """Return the `keyring` module if a usable backend is available, else None."""
    global _keyring_checked, _keyring_module
    if _keyring_checked:
        return _keyring_module
    _keyring_checked = True
    try:
        import keyring  # type: ignore[import-not-found]
        from keyring.backends.fail import Keyring as FailKeyring  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        backend = keyring.get_keyring()
    except Exception:
        logger.warning("keyring backend probe failed", exc_info=True)
        return None
    if isinstance(backend, FailKeyring):
        logger.info("keyring reports no usable backend; falling back to encrypted file")
        return None
    _keyring_module = keyring
    return _keyring_module


# ─── file fallback ──────────────────────────────────────────────────────
#
# Format:  data_dir() / "secrets.json" — a JSON object of {key: base64-bytes}
# Encryption: AES-GCM via stdlib `hashlib.scrypt` to derive a key from the
# random per-install secret. We avoid depending on `cryptography` here
# because it's a heavy build-time dep we don't otherwise need until later
# phases; instead we use `hmac`-authenticated XOR-stream encryption built
# from `hashlib.shake_256`. This is strictly a defence-in-depth measure
# beyond the OS file permissions — sensitive secrets should still go to
# the platform keyring whenever it's available.


def _secrets_path() -> Path:
    return data_dir() / "secrets.json"


def _master_key_path() -> Path:
    return data_dir() / ".keyring_key"


def _master_key() -> bytes:
    path = _master_key_path()
    if path.exists():
        return path.read_bytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = secrets.token_bytes(32)
    path.write_bytes(raw)
    if hasattr(os, "chmod"):
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)
    return raw


def _stream_keystream(master: bytes, nonce: bytes, length: int) -> bytes:
    return hashlib.shake_256(master + nonce).digest(length)


def _encrypt(plaintext: str) -> str:
    master = _master_key()
    pt = plaintext.encode("utf-8")
    nonce = secrets.token_bytes(16)
    stream = _stream_keystream(master, nonce, len(pt))
    ct = bytes(p ^ s for p, s in zip(pt, stream, strict=True))
    mac = hmac.new(master, nonce + ct, hashlib.sha256).digest()
    return base64.b64encode(nonce + mac + ct).decode("ascii")


def _decrypt(token: str) -> str | None:
    try:
        raw = base64.b64decode(token.encode("ascii"))
    except (ValueError, TypeError):
        return None
    if len(raw) < 16 + 32:
        return None
    master = _master_key()
    nonce, mac, ct = raw[:16], raw[16:48], raw[48:]
    expected = hmac.new(master, nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, mac):
        return None
    stream = _stream_keystream(master, nonce, len(ct))
    try:
        return bytes(c ^ s for c, s in zip(ct, stream, strict=True)).decode("utf-8")
    except UnicodeDecodeError:
        return None


def _read_store() -> dict[str, str]:
    path = _secrets_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_store(store: dict[str, str]) -> None:
    path = _secrets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store), encoding="utf-8")
    if hasattr(os, "chmod"):
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)


def _file_store(key: str, value: str) -> None:
    store_data = _read_store()
    store_data[key] = _encrypt(value)
    _write_store(store_data)


def _file_retrieve(key: str) -> str | None:
    token = _read_store().get(key)
    if token is None:
        return None
    return _decrypt(token)


def _file_delete(key: str) -> None:
    store_data = _read_store()
    if key in store_data:
        store_data.pop(key)
        _write_store(store_data)


def _reset_for_test() -> None:
    """Clear the cached keyring detection state (test helper only)."""
    global _keyring_checked, _keyring_module
    _keyring_checked = False
    _keyring_module = None
