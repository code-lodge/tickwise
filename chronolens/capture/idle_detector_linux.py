"""Linux implementation of idle-time detection.

Tries (in order):
1. `xprintidle` (X11) — small one-shot binary, returns ms.
2. `swayidle`-style query via `swaymsg` is unavailable, so for Wayland we
   fall back to the `org.freedesktop.ScreenSaver` D-Bus method
   `GetSessionIdleTime` via `dbus-send`.
3. xss-query via XScreenSaverQueryInfo through python-xlib — only used if
   the first two paths failed and python-xlib is importable.

Returns 0.0 if no path works (headless session, missing tools).
"""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def _idle_via_xprintidle() -> float | None:
    if not shutil.which("xprintidle"):
        return None
    try:
        out = subprocess.run(  # noqa: S603,S607
            ["xprintidle"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        return int(out.stdout.strip()) / 1000.0
    except ValueError:
        return None


def _idle_via_dbus() -> float | None:
    if not shutil.which("dbus-send"):
        return None
    try:
        out = subprocess.run(  # noqa: S603,S607
            [
                "dbus-send",
                "--session",
                "--print-reply=literal",
                "--dest=org.freedesktop.ScreenSaver",
                "/org/freedesktop/ScreenSaver",
                "org.freedesktop.ScreenSaver.GetSessionIdleTime",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    # Reply looks like "   uint32 12345"; we want the trailing integer.
    for token in reversed(out.stdout.split()):
        try:
            return int(token) / 1000.0
        except ValueError:
            continue
    return None


def _idle_via_xlib() -> float | None:
    try:
        from Xlib import display as xdisplay
        from Xlib.ext import screensaver  # noqa: F401
    except ImportError:
        return None
    try:
        d = xdisplay.Display()
        info = d.screen().root.screensaver_query_info()
        return float(info.idle) / 1000.0
    except Exception:
        logger.debug("Xlib idle query failed", exc_info=True)
        return None


def get_idle_seconds() -> float:
    """Seconds since last input on Linux (X11 or Wayland), or 0.0 on failure."""
    for source in (_idle_via_xprintidle, _idle_via_dbus, _idle_via_xlib):
        secs = source()
        if secs is not None and secs >= 0:
            return secs
    return 0.0
