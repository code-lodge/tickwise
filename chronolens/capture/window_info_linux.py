"""Linux implementation of window-info queries.

Tries Sway IPC first (Wayland with sway/i3 — the cleanest path), then
falls back to `xdotool` for X11. Process name comes from `/proc/{pid}/comm`
which is always present on Linux even without psutil.

Returns an empty WindowInfo if no supported method works (pure Wayland
without sway, headless session, etc.).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from chronolens.capture.window_info import WindowInfo

logger = logging.getLogger(__name__)


def _process_name(pid: int) -> str:
    """Read the process name from /proc/{pid}/comm. Returns "" on error."""
    if pid <= 0:
        return ""
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return ""


def _focused_from_sway() -> WindowInfo | None:
    """Walk Sway's tree looking for the focused node."""
    sway_sock = os.environ.get("SWAYSOCK") or os.environ.get("I3SOCK")
    if not sway_sock or not shutil.which("swaymsg"):
        return None
    try:
        out = subprocess.run(  # noqa: S603,S607 — fixed argv, no shell
            ["swaymsg", "-t", "get_tree"],
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
        tree = json.loads(out.stdout)
    except ValueError:
        return None

    def _find_focused(node: dict[str, Any]) -> dict[str, Any] | None:
        if node.get("focused"):
            return node
        for child_key in ("nodes", "floating_nodes"):
            for child in node.get(child_key, []) or []:
                hit = _find_focused(child)
                if hit is not None:
                    return hit
        return None

    focused = _find_focused(tree)
    if focused is None:
        return None
    pid = int(focused.get("pid") or 0) or None
    title = str(focused.get("name") or "")
    proc = _process_name(pid) if pid else ""
    return WindowInfo(title=title, process_name=proc, pid=pid)


def _focused_from_xdotool() -> WindowInfo | None:
    """Use xdotool to grab the active window's name and pid."""
    if not shutil.which("xdotool"):
        return None
    try:
        wid = subprocess.run(  # noqa: S603,S607
            ["xdotool", "getactivewindow"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if wid.returncode != 0 or not wid.stdout.strip():
            return None
        win_id = wid.stdout.strip()
        name = subprocess.run(  # noqa: S603,S607
            ["xdotool", "getwindowname", win_id],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        pid_out = subprocess.run(  # noqa: S603,S607
            ["xdotool", "getwindowpid", win_id],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    title = name.stdout.strip() if name.returncode == 0 else ""
    try:
        pid: int | None = int(pid_out.stdout.strip()) or None
    except ValueError:
        pid = None
    proc = _process_name(pid) if pid else ""
    return WindowInfo(title=title, process_name=proc, pid=pid)


def get_active_window() -> WindowInfo:
    """Return the focused window via Sway IPC (Wayland) or xdotool (X11)."""
    for finder in (_focused_from_sway, _focused_from_xdotool):
        info = finder()
        if info is not None:
            return info
    return WindowInfo(title="", process_name="", pid=None)


def get_window_center() -> tuple[int, int] | None:
    """Return the focused window's centre via Sway IPC or xdotool, or None."""
    sway_sock = os.environ.get("SWAYSOCK") or os.environ.get("I3SOCK")
    if sway_sock and shutil.which("swaymsg"):
        try:
            out = subprocess.run(  # noqa: S603,S607
                ["swaymsg", "-t", "get_tree"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            if out.returncode == 0:
                tree = json.loads(out.stdout)

                def _find_focused(node: dict[str, Any]) -> dict[str, Any] | None:
                    if node.get("focused"):
                        return node
                    for child_key in ("nodes", "floating_nodes"):
                        for child in node.get(child_key, []) or []:
                            hit = _find_focused(child)
                            if hit is not None:
                                return hit
                    return None

                focused = _find_focused(tree)
                if focused is not None:
                    rect = focused.get("rect") or {}
                    x = int(rect.get("x", 0)) + int(rect.get("width", 0)) // 2
                    y = int(rect.get("y", 0)) + int(rect.get("height", 0)) // 2
                    return (x, y)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass

    if shutil.which("xdotool"):
        try:
            geom = subprocess.run(  # noqa: S603,S607
                ["xdotool", "getactivewindow", "getwindowgeometry", "--shell"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if geom.returncode == 0:
            values: dict[str, int] = {}
            import contextlib

            for line in geom.stdout.splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    with contextlib.suppress(ValueError):
                        values[k.strip()] = int(v.strip())
            if "X" in values and "Y" in values and "WIDTH" in values and "HEIGHT" in values:
                return (values["X"] + values["WIDTH"] // 2, values["Y"] + values["HEIGHT"] // 2)
    return None
