"""Active-window information dispatcher.

Selects the platform-specific implementation at import time. Each backend
exposes the same `WindowInfo` dataclass and `get_active_window()` function.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """Snapshot of the currently focused window."""

    title: str
    process_name: str
    pid: int | None


def _unsupported() -> WindowInfo:
    return WindowInfo(title="", process_name="", pid=None)


if sys.platform == "win32":
    from chronolens.capture.window_info_windows import (
        get_active_window as get_active_window,
    )
    from chronolens.capture.window_info_windows import (
        get_window_center as get_window_center,
    )
elif sys.platform == "darwin":
    from chronolens.capture.window_info_macos import (
        get_active_window as get_active_window,
    )
    from chronolens.capture.window_info_macos import (
        get_window_center as get_window_center,
    )
elif sys.platform.startswith("linux"):
    from chronolens.capture.window_info_linux import (
        get_active_window as get_active_window,
    )
    from chronolens.capture.window_info_linux import (
        get_window_center as get_window_center,
    )
else:  # pragma: no cover — exotic platform fallback

    def get_active_window() -> WindowInfo:
        """Return an empty WindowInfo on unsupported platforms."""
        return _unsupported()

    def get_window_center() -> tuple[int, int] | None:
        return None


__all__ = ["WindowInfo", "get_active_window", "get_window_center"]
