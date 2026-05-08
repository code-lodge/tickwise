"""Locate or download the `cloudflared` binary.

We ship without the binary — too large, too platform-specific — and
fetch it from the official GitHub release on first activation. The file
lands in ``data_dir() / bin / cloudflared[.exe]`` so subsequent runs
can skip the download.
"""

from __future__ import annotations

import hashlib
import logging
import platform
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

from tickwise.platform.paths import data_dir

logger = logging.getLogger(__name__)

_GH_LATEST = "https://github.com/cloudflare/cloudflared/releases/latest/download/"
_DOWNLOAD_TIMEOUT = 60.0


@dataclass(frozen=True, slots=True)
class BinaryTarget:
    """Where the binary lives on disk and how to fetch it."""

    asset_name: str
    local_filename: str

    @property
    def url(self) -> str:
        return f"{_GH_LATEST}{self.asset_name}"


def _binary_target() -> BinaryTarget:
    machine = platform.machine().lower()
    is_arm64 = machine in {"arm64", "aarch64"}
    if sys.platform == "win32":
        return BinaryTarget("cloudflared-windows-amd64.exe", "cloudflared.exe")
    if sys.platform == "darwin":
        asset = "cloudflared-darwin-arm64.tgz" if is_arm64 else "cloudflared-darwin-amd64.tgz"
        return BinaryTarget(asset, "cloudflared")
    asset = "cloudflared-linux-arm64" if is_arm64 else "cloudflared-linux-amd64"
    return BinaryTarget(asset, "cloudflared")


def binary_path() -> Path:
    """Return the resolved path where cloudflared should live."""
    return data_dir() / "bin" / _binary_target().local_filename


def is_installed() -> bool:
    """True iff the binary is present and (on POSIX) executable."""
    target = binary_path()
    if not target.is_file():
        return False
    if sys.platform != "win32" and not target.stat().st_mode & stat.S_IXUSR:
        return False
    return True


def ensure_binary(*, force: bool = False, http: httpx.Client | None = None) -> Path:
    """Download cloudflared if it's missing (or `force=True`).

    Raises:
        RuntimeError: if the download fails or the network is unreachable.
    """
    target = binary_path()
    if not force and is_installed():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    spec = _binary_target()
    logger.info("Downloading cloudflared from %s", spec.url)
    payload = _download(spec.url, http)
    if spec.asset_name.endswith(".tgz"):
        _extract_tgz(payload, target)
    else:
        target.write_bytes(payload)
    if sys.platform != "win32":
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    logger.info("cloudflared installed at %s (%d bytes)", target, target.stat().st_size)
    return target


def sha256_of_installed() -> str | None:
    """Return the SHA-256 of the local binary, or None if it isn't there."""
    target = binary_path()
    if not target.is_file():
        return None
    h = hashlib.sha256()
    with target.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ─── internals ──────────────────────────────────────────────────────────


def _download(url: str, http: httpx.Client | None) -> bytes:
    if http is not None:
        response = http.get(url, follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT)
    else:
        with httpx.Client(follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT) as transient:
            response = transient.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"cloudflared download failed: HTTP {response.status_code}")
    return response.content


def _extract_tgz(payload: bytes, target: Path) -> None:
    """macOS releases ship as `.tgz` archives. Extract the single binary."""
    import io
    import tarfile

    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        member = next(
            (m for m in tar.getmembers() if m.isfile() and m.name.endswith("cloudflared")),
            None,
        )
        if member is None:
            raise RuntimeError("cloudflared not found inside downloaded archive")
        extracted = tar.extractfile(member)
        if extracted is None:
            raise RuntimeError("could not read cloudflared from archive")
        target.write_bytes(extracted.read())


def remove_binary() -> bool:
    """Delete the cached binary, returning True iff a file was removed."""
    target = binary_path()
    if not target.is_file():
        return False
    target.unlink()
    return True


def _wipe_for_test() -> None:
    """Remove the entire bin/ directory — test helper only."""
    shutil.rmtree(binary_path().parent, ignore_errors=True)
