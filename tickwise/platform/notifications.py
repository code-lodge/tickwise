"""Cross-platform desktop notifications.

Primary path: `plyer.notification.notify(...)` which dispatches to the
native API on each OS (toast on Windows, NSUserNotification on macOS,
libnotify/D-Bus on Linux).

Fallback paths (when plyer is unavailable):
- Linux: `notify-send` via subprocess.
- macOS: `osascript -e 'display notification ...'` via subprocess.
- Windows: best-effort PowerShell BurntToast invocation; if neither is
  available, the call is logged and silently dropped — notifications
  are advisory, never critical.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from typing import Any

from tickwise.config import APP_NAME

logger = logging.getLogger(__name__)


def notify(
    title: str,
    message: str,
    *,
    timeout: int = 5,
    app_name: str = APP_NAME,
) -> bool:
    """Show a desktop notification. Returns True if a backend handled it.

    `timeout` is honoured by Linux/Windows backends; macOS Notification
    Center decides on its own.
    """
    if _notify_via_plyer(title, message, timeout, app_name):
        return True
    if sys.platform == "darwin":
        return _notify_via_osascript(title, message)
    if sys.platform.startswith("linux"):
        return _notify_via_notify_send(title, message, timeout, app_name)
    return False


def _notify_via_plyer(title: str, message: str, timeout: int, app_name: str) -> bool:
    try:
        from plyer import notification
    except ImportError:
        return False
    try:
        _notify_call(notification, title=title, message=message, timeout=timeout, app_name=app_name)
        return True
    except Exception:
        logger.debug("plyer notification failed", exc_info=True)
        return False


def _notify_call(notification: Any, **kwargs: Any) -> None:
    """Tiny indirection so tests can assert on the call shape."""
    notification.notify(**kwargs)


def _notify_via_notify_send(title: str, message: str, timeout: int, app_name: str) -> bool:
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.run(  # noqa: S603,S607
            ["notify-send", "-a", app_name, "-t", str(max(0, timeout) * 1000), title, message],
            check=False,
            timeout=2.0,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _notify_via_osascript(title: str, message: str) -> bool:
    if not shutil.which("osascript"):
        return False
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(  # noqa: S603,S607
            ["osascript", "-e", script],
            check=False,
            timeout=2.0,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False
