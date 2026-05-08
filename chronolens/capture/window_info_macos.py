"""macOS implementation of window-info queries.

Uses pyobjc's `AppKit.NSWorkspace` to identify the frontmost application.
The window title comes from the Accessibility API (`AXUIElement`) which
requires the user to grant Accessibility permission to ChronoLens in
System Settings → Privacy & Security; without it, the title falls back
to the empty string.

If pyobjc is not installed (e.g. under headless CI on Linux/Windows),
`get_active_window()` returns an empty WindowInfo rather than raising.
"""

from __future__ import annotations

import logging
from typing import Any

from chronolens.capture.window_info import WindowInfo

logger = logging.getLogger(__name__)


def _frontmost_app() -> Any:
    """Return the NSRunningApplication for the frontmost app, or None."""
    try:
        from AppKit import NSWorkspace
    except ImportError:
        return None
    workspace = NSWorkspace.sharedWorkspace()
    return workspace.frontmostApplication()


def _accessibility_window_title(pid: int) -> str:
    """Return the focused window title for `pid` via the Accessibility API.

    Returns "" if Accessibility access is not granted, the API call fails,
    or pyobjc/HIServices isn't available.
    """
    try:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
            kAXFocusedWindowAttribute,
            kAXTitleAttribute,
        )
    except ImportError:
        return ""
    try:
        app = AXUIElementCreateApplication(pid)
        err, focused = AXUIElementCopyAttributeValue(app, kAXFocusedWindowAttribute, None)
        if err or focused is None:
            return ""
        err, title = AXUIElementCopyAttributeValue(focused, kAXTitleAttribute, None)
        if err or title is None:
            return ""
        return str(title)
    except Exception:
        logger.debug("Accessibility query failed", exc_info=True)
        return ""


def get_active_window() -> WindowInfo:
    """Return the frontmost-app's process name and focused-window title.

    Falls back to (process_name, "") if Accessibility isn't granted, and
    to an empty WindowInfo if pyobjc isn't installed.
    """
    app = _frontmost_app()
    if app is None:
        return WindowInfo(title="", process_name="", pid=None)
    name = str(app.localizedName() or "")
    pid = int(app.processIdentifier() or 0) or None
    title = _accessibility_window_title(pid) if pid else ""
    return WindowInfo(title=title, process_name=name, pid=pid)
