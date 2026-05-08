"""Autostart-on-login dispatcher.

Each platform-specific backend exposes the same three operations:

- `enable(command)` — register ChronoLens to launch at login.
- `disable()` — remove the autostart registration.
- `is_enabled()` — return True iff the registration is currently present.

`command` is the exact shell-ready string the OS should run; for the
default app, callers pass `default_launch_command()` which produces the
`python -m chronolens` invocation that mirrors how the user starts the
process today.
"""

from __future__ import annotations

import shlex
import sys


def default_launch_command() -> str:
    """Return the canonical `python -m chronolens` command for the current Python."""
    return f"{shlex.quote(sys.executable)} -m chronolens"


if sys.platform == "win32":
    from chronolens.platform.autostart_windows import disable, enable, is_enabled
elif sys.platform == "darwin":
    from chronolens.platform.autostart_macos import disable, enable, is_enabled
elif sys.platform.startswith("linux"):
    from chronolens.platform.autostart_linux import disable, enable, is_enabled
else:  # pragma: no cover

    def enable(_command: str) -> None:
        raise NotImplementedError("Autostart is not supported on this platform")

    def disable() -> None:
        raise NotImplementedError("Autostart is not supported on this platform")

    def is_enabled() -> bool:
        return False


__all__ = ["default_launch_command", "disable", "enable", "is_enabled"]
