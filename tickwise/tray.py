"""System tray icon using pystray + Pillow.

Phase 1 wires the tray menu to the live `CaptureLoop` and `SessionTracker`
held in `tickwise.runtime`. The tray text refreshes every few seconds in
a small daemon thread so the user sees the current process and a running
"today's total".
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from tickwise import runtime
from tickwise.config import API_HOST, API_PORT
from tickwise.sessions.tracker import today_total_seconds


def _find_electron_install() -> "Path | None":
    """Locate the Electron-built Tickwise app on this machine, or None.

    Electron-builder's NSIS installer drops a `resources/app.asar` next
    to the executable — that's the marker we use to distinguish a real
    Electron install from this PyInstaller bundle (which is also called
    Tickwise.exe and would otherwise loop).
    """
    import os
    import sys
    from pathlib import Path

    candidates: list[Path] = []
    if sys.platform == "win32":
        for env in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
            base = os.environ.get(env)
            if not base:
                continue
            candidates.append(Path(base) / "Programs" / "Tickwise" / "Tickwise.exe")
            candidates.append(Path(base) / "Tickwise" / "Tickwise.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Tickwise.app/Contents/MacOS/Tickwise"))
        candidates.append(Path.home() / "Applications/Tickwise.app/Contents/MacOS/Tickwise")
    elif sys.platform.startswith("linux"):
        candidates.append(Path.home() / "Applications" / "Tickwise.AppImage")
        candidates.append(Path("/opt/Tickwise/tickwise"))

    for cand in candidates:
        if not cand.is_file():
            continue
        # Distinguish Electron from this PyInstaller exe: Electron always
        # ships a resources/app.asar (Win/Linux) or Resources/app.asar (mac).
        for asar in (cand.parent / "resources" / "app.asar", cand.parent.parent / "Resources" / "app.asar"):
            if asar.is_file():
                return cand
    return None


def _open_dashboard() -> None:
    """Open the dashboard.

    Prefers the Electron-built Tickwise app — it provides the proper
    "open in its own window" experience the user expects from clicking
    Open Dashboard. Electron's single-instance lock makes the Popen
    idempotent: if it's already running, the new process focuses the
    existing window and exits.

    Falls back to the default browser when the Electron app isn't
    installed (dev mode, or running the standalone PyInstaller exe).
    """
    import subprocess
    import webbrowser

    electron = _find_electron_install()
    if electron is not None:
        try:
            subprocess.Popen([str(electron)], close_fds=True)
            return
        except Exception as exc:  # noqa: BLE001 — fall back rather than crash
            logger.warning("Failed to launch Electron app, falling back to browser: %s", exc)

    webbrowser.open(f"http://{API_HOST}:{API_PORT}/")


try:
    import pystray
    from PIL import Image  # noqa: F401  (used at runtime in _build_icon_image)

    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False

logger = logging.getLogger(__name__)

_ICON_SIZE = 64
_REFRESH_SECONDS = 5.0

# Spec §12 tray-icon state palette. Phase 1 uses tracking / paused / idle;
# the remaining states (focus, break, error, no-LLM) come online with
# Phase 3 (LLM) and Phase 7 (Pomodoro).
_COLOR_TRACKING = "#22C55E"  # green
_COLOR_PAUSED = "#EAB308"  # yellow
_COLOR_IDLE = "#9CA3AF"  # gray
_COLOR_NEUTRAL = "#3B82F6"  # blue (pre-startup)
_COLOR_FOCUS = "#EF4444"  # red — pomodoro focus
_COLOR_BREAK = "#06B6D4"  # cyan — pomodoro break


def _icon_color() -> str:
    """Pick the tray icon colour from the current runtime state."""
    timer = runtime.get_pomodoro_timer()
    if timer is not None:
        snap = timer.snapshot()
        if snap.state.value == "focus":
            return _COLOR_FOCUS
        if snap.state.value in ("short_break", "long_break"):
            return _COLOR_BREAK
    loop = runtime.get_capture_loop()
    if loop is None or not loop.is_running:
        return _COLOR_NEUTRAL
    if loop.is_paused:
        return _COLOR_PAUSED
    if loop.last_idle_seconds and loop.last_idle_seconds >= 300.0:
        return _COLOR_IDLE
    return _COLOR_TRACKING


def _build_icon_image(color: str = _COLOR_NEUTRAL) -> Any:
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
    timer = runtime.get_pomodoro_timer()
    if timer is not None:
        snap = timer.snapshot()
        if snap.state.value != "idle":
            label = {
                "focus": "Focus",
                "short_break": "Short break",
                "long_break": "Long break",
            }.get(snap.state.value, snap.state.value)
            return f"Tickwise — {label} · {_format_duration(snap.remaining_secs)} left"
    loop = runtime.get_capture_loop()
    tracker = runtime.get_session_tracker()
    if loop is None or not loop.is_running:
        return "Tickwise — Not tracking"
    if loop.is_paused:
        return "Tickwise — Paused"
    process = loop.last_window.process_name or "—"
    open_session = tracker.open_session if tracker else None
    duration = ""
    if open_session is not None:
        secs = int((datetime.now(UTC) - open_session.started_at).total_seconds())
        duration = f" · {_format_duration(secs)}"
    return f"Tickwise — {process}{duration}"


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

    def _toggle_focus(_icon: Any, _item: Any) -> None:
        timer = runtime.get_pomodoro_timer()
        if timer is None:
            return
        if timer.snapshot().state.value == "idle":
            timer.start_focus()
        else:
            timer.stop()

    def _focus_label(_item: Any) -> str:
        timer = runtime.get_pomodoro_timer()
        if timer is None:
            return "Start Focus"
        return "Stop Pomodoro" if timer.snapshot().state.value != "idle" else "Start Focus"

    def _quit_action(icon: Any, _item: Any) -> None:
        icon.stop()
        on_quit()

    icon = pystray.Icon(
        name="Tickwise",
        icon=_build_icon_image(_icon_color()),
        title=build_status_text(),
        menu=pystray.Menu(
            pystray.MenuItem(lambda _item: build_status_text(), None, enabled=False),
            pystray.MenuItem(lambda _item: build_today_total_text(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Dashboard", lambda _icon, _item: _open_dashboard()),
            pystray.MenuItem(
                lambda _item: "Resume Tracking" if _is_paused(_item) else "Pause Tracking",
                _toggle_pause,
            ),
            pystray.MenuItem(_focus_label, _toggle_focus),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", _quit_action),
        ),
    )

    stop_refresh = threading.Event()

    def _refresh_loop() -> None:
        last_color = _icon_color()
        while not stop_refresh.wait(_REFRESH_SECONDS):
            try:
                icon.title = build_status_text()
                color = _icon_color()
                if color != last_color:
                    icon.icon = _build_icon_image(color)
                    last_color = color
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
