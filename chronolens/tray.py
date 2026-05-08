"""System tray icon using pystray + Pillow.

Phase 1 wires the tray menu to the live `CaptureLoop` and `SessionTracker`
held in `chronolens.runtime`. The tray text refreshes every few seconds in
a small daemon thread so the user sees the current process and a running
"today's total".
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from chronolens import runtime
from chronolens.sessions.tracker import today_total_seconds

try:
    import pystray
    from PIL import Image  # noqa: F401  (used at runtime in _build_icon_image)

    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False

logger = logging.getLogger(__name__)

_ICON_SIZE = 64
_REFRESH_SECONDS = 5.0


def _build_icon_image(color: str = "#3B82F6") -> Any:
    """Draw a simple clock-face icon for the tray."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy, r = _ICON_SIZE // 2, _ICON_SIZE // 2, _ICON_SIZE // 2 - 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    # Hour hand
    draw.line([cx, cy, cx, cy - r // 2], fill="white", width=3)
    # Minute hand
    draw.line([cx, cy, cx + r // 2, cy], fill="white", width=2)
    return img


def _format_duration(seconds: int) -> str:
    """Render seconds as `Hh MMm` (or `MMm SSs` if < 1h)."""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


def build_status_text() -> str:
    """Compose the tooltip / first-line label from runtime state.

    Pure function over `runtime` getters — exposed for tests.
    """
    loop = runtime.get_capture_loop()
    tracker = runtime.get_session_tracker()
    if loop is None or not loop.is_running:
        return "ChronoLens — Not tracking"
    if loop.is_paused:
        return "ChronoLens — Paused"
    process = loop.last_window.process_name or "—"
    open_session = tracker.open_session if tracker else None
    duration = ""
    if open_session is not None:
        secs = int((datetime.now(UTC) - open_session.started_at).total_seconds())
        duration = f" · {_format_duration(secs)}"
    return f"ChronoLens — {process}{duration}"


def build_today_total_text() -> str:
    """Return a `XhYYm today` label, or empty string on DB failure."""
    try:
        total = today_total_seconds()
    except Exception:
        return ""
    return f"{_format_duration(total)} today"


def run_tray(on_quit: Callable[[], None]) -> None:
    """Start the system tray icon (blocks until the user quits).

    This function must be called from the main thread on macOS.

    Args:
        on_quit: Callback invoked when the user selects Quit from the tray menu.
    """
    if not _PYSTRAY_AVAILABLE:
        logger.warning("pystray/Pillow not installed — tray icon unavailable")
        threading.Event().wait()
        return

    def _toggle_pause(_icon: Any, _item: Any) -> None:
        loop = runtime.get_capture_loop()
        if loop is None:
            return
        if loop.is_paused:
            loop.resume()
        else:
            loop.pause()

    def _is_paused(_item: Any) -> bool:
        loop = runtime.get_capture_loop()
        return bool(loop and loop.is_paused)

    def _quit_action(icon: Any, _item: Any) -> None:
        icon.stop()
        on_quit()

    icon = pystray.Icon(
        name="ChronoLens",
        icon=_build_icon_image(),
        title=build_status_text(),
        menu=pystray.Menu(
            pystray.MenuItem(build_status_text, None, enabled=False),
            pystray.MenuItem(build_today_total_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", lambda: None),
            pystray.MenuItem(
                lambda _item: "Resume Tracking" if _is_paused(_item) else "Pause Tracking",
                _toggle_pause,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", _quit_action),
        ),
    )

    stop_refresh = threading.Event()

    def _refresh_loop() -> None:
        while not stop_refresh.wait(_REFRESH_SECONDS):
            try:
                icon.title = build_status_text()
                icon.update_menu()
            except Exception:
                logger.exception("tray refresh failed")

    refresher = threading.Thread(target=_refresh_loop, name="tray-refresh", daemon=True)
    refresher.start()

    logger.info("Starting system tray icon")
    try:
        icon.run()
    finally:
        stop_refresh.set()
