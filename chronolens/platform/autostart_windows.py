"""Windows autostart via the per-user `Run` registry key.

Writes `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\ChronoLens`
with the launch command so ChronoLens starts automatically when the user
signs in. We use the per-user hive (no admin elevation required).
"""

from __future__ import annotations

import sys
import winreg  # type: ignore[import-not-found,unused-ignore]  # stdlib on Windows only

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "ChronoLens"

if sys.platform != "win32":  # pragma: no cover — guard against accidental import
    raise OSError("autostart_windows is Windows-only")


def enable(command: str) -> None:
    """Create or overwrite the autostart entry."""
    with winreg.OpenKey(  # type: ignore[attr-defined,unused-ignore]
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, command)  # type: ignore[attr-defined,unused-ignore]


def disable() -> None:
    """Remove the autostart entry. Safe to call when not present."""
    try:
        with winreg.OpenKey(  # type: ignore[attr-defined,unused-ignore]
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _VALUE_NAME)  # type: ignore[attr-defined,unused-ignore]
    except FileNotFoundError:
        pass


def is_enabled() -> bool:
    """True iff a `ChronoLens` value exists under the Run key."""
    try:
        with winreg.OpenKey(  # type: ignore[attr-defined,unused-ignore]
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, _VALUE_NAME)  # type: ignore[attr-defined,unused-ignore]
        return True
    except FileNotFoundError:
        return False
