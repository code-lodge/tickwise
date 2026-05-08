"""Manage the local `cloudflared` subprocess.

The tunnel manager owns one long-running child process. Once started it
streams a "named-tunnel run" command bound to the tunnel id stored in
``cloudflare_config``. Health is judged by the process being alive and
the most recent stderr line not signalling an unrecoverable error.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tickwise.cloudflare.binary import binary_path, ensure_binary

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TunnelStatus:
    """Plain-data snapshot for the API."""

    running: bool
    pid: int | None = None
    last_log_line: str | None = None
    last_error: str | None = None


class TunnelManager:
    """Single-process orchestrator with a tiny rolling log buffer."""

    def __init__(self) -> None:
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()
        self._log: deque[str] = deque(maxlen=50)
        self._reader_thread: threading.Thread | None = None
        self._last_error: str | None = None

    # ─── lifecycle ──────────────────────────────────────────────────────

    def start(
        self,
        tunnel_token: str,
        *,
        binary: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> TunnelStatus:
        """Spawn cloudflared if it isn't already running. Returns status."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return self._status_locked()
            cloudflared = binary or binary_path()
            if not cloudflared.exists():
                cloudflared = ensure_binary()
            args = [str(cloudflared), "tunnel", "--no-autoupdate", "run", "--token", tunnel_token]
            try:
                self._process = subprocess.Popen(  # noqa: S603 — fixed argv, validated path
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=env,
                )
            except (OSError, FileNotFoundError) as exc:
                self._last_error = str(exc)
                self._process = None
                return TunnelStatus(running=False, last_error=str(exc))
            self._reader_thread = threading.Thread(target=self._drain_output, name="cloudflared-log", daemon=True)
            self._reader_thread.start()
            self._last_error = None
            return self._status_locked()

    def stop(self, timeout: float = 5.0) -> None:
        """Terminate the process if it's running."""
        with self._lock:
            if self._process is None:
                return
            try:
                self._process.terminate()
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception:  # noqa: BLE001
                logger.exception("cloudflared termination failed")
            finally:
                self._process = None

    def status(self) -> TunnelStatus:
        with self._lock:
            return self._status_locked()

    # ─── helpers ────────────────────────────────────────────────────────

    def _status_locked(self) -> TunnelStatus:
        if self._process is None:
            return TunnelStatus(running=False, last_error=self._last_error)
        running = self._process.poll() is None
        return TunnelStatus(
            running=running,
            pid=self._process.pid if running else None,
            last_log_line=self._log[-1] if self._log else None,
            last_error=self._last_error,
        )

    def _drain_output(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            for raw in iter(process.stdout.readline, b""):
                line = raw.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                self._log.append(line)
                if "error" in line.lower():
                    self._last_error = line
        except Exception:  # noqa: BLE001
            logger.exception("cloudflared log reader crashed")


# Module-level singleton — there's only ever one tunnel per app instance.
_manager_singleton: TunnelManager | None = None


def get_manager() -> TunnelManager:
    global _manager_singleton
    if _manager_singleton is None:
        _manager_singleton = TunnelManager()
    return _manager_singleton


def cloudflared_available() -> bool:
    """True iff cloudflared is on PATH or already downloaded."""
    return binary_path().is_file() or bool(shutil.which("cloudflared"))


def reset_for_test() -> None:
    """Reset the singleton — test helper only."""
    global _manager_singleton
    _manager_singleton = None


def _coerce_for_typing(_x: Any) -> None:  # noqa: D401 — keep mypy happy on stub re-exports
    return None
