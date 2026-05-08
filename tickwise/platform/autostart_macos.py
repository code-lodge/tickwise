"""macOS autostart via `~/Library/LaunchAgents/com.tickwise.plist`.

The launchd plist defines `RunAtLoad=true` and `KeepAlive=false` — we
want the agent to start at login but not be respawned if the user quits
intentionally from the tray.
"""

from __future__ import annotations

import contextlib
import plistlib
import shlex
from pathlib import Path

_LABEL = "com.tickwise"


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_LABEL}.plist"


def _build_plist(command: str) -> bytes:
    program_args = shlex.split(command)
    payload: dict[str, object] = {
        "Label": _LABEL,
        "ProgramArguments": program_args,
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
    }
    return plistlib.dumps(payload)


def enable(command: str) -> None:
    """Write the LaunchAgent plist for the given command."""
    target = _plist_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_build_plist(command))


def disable() -> None:
    """Remove the LaunchAgent plist. Safe to call when not present."""
    target = _plist_path()
    with contextlib.suppress(FileNotFoundError):
        target.unlink()


def is_enabled() -> bool:
    """True iff the plist exists on disk."""
    return _plist_path().is_file()
