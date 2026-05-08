"""Linux autostart via XDG `~/.config/autostart/chronolens.desktop`.

The XDG Autostart spec (freedesktop.org) is honoured by all major
desktop environments — GNOME, KDE, XFCE, Cinnamon, MATE. The .desktop
file is a small INI-flavoured manifest pointing at the launch command.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

_FILENAME = "chronolens.desktop"


def _autostart_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "autostart"


def _desktop_path() -> Path:
    return _autostart_dir() / _FILENAME


def _build_desktop(command: str) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=ChronoLens\n"
        "Comment=Privacy-conscious automatic time tracking\n"
        f"Exec={command}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def enable(command: str) -> None:
    """Write the .desktop autostart entry for the given command."""
    target = _desktop_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_build_desktop(command), encoding="utf-8")
    target.chmod(0o644)


def disable() -> None:
    """Remove the .desktop entry. Safe to call when not present."""
    target = _desktop_path()
    with contextlib.suppress(FileNotFoundError):
        target.unlink()


def is_enabled() -> bool:
    """True iff the .desktop entry exists on disk."""
    return _desktop_path().is_file()
