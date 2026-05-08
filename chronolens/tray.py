"""System tray icon using pystray + Pillow."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

try:
    import pystray
    from PIL import Image  # noqa: F401  (used at runtime in _build_icon_image)

    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False

logger = logging.getLogger(__name__)

_ICON_SIZE = 64


def _build_icon_image() -> Any:
    """Draw a simple clock-face icon for the tray."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = _ICON_SIZE // 2, _ICON_SIZE // 2, _ICON_SIZE // 2 - 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#3B82F6")
    # Hour hand
    draw.line([cx, cy, cx, cy - r // 2], fill="white", width=3)
    # Minute hand
    draw.line([cx, cy, cx + r // 2, cy], fill="white", width=2)
    return img


def run_tray(on_quit: Callable[[], None]) -> None:
    """Start the system tray icon (blocks until the user quits).

    This function must be called from the main thread on macOS.

    Args:
        on_quit: Callback invoked when the user selects Quit from the tray menu.
    """
    if not _PYSTRAY_AVAILABLE:
        logger.warning("pystray/Pillow not installed — tray icon unavailable")
        # Keep the main thread alive so the API server can still run.
        threading.Event().wait()
        return

    def _quit_action(icon: Any, _item: Any) -> None:
        icon.stop()
        on_quit()

    icon = pystray.Icon(
        name="ChronoLens",
        icon=_build_icon_image(),
        title="ChronoLens — Not tracking",
        menu=pystray.Menu(
            pystray.MenuItem("Not tracking", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", lambda: None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", _quit_action),
        ),
    )
    logger.info("Starting system tray icon")
    icon.run()
