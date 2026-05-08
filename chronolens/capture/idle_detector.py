"""Idle-time detector dispatcher.

Returns the number of seconds since the user's last keyboard or mouse input.
Platform-specific backends are selected at import time.
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from chronolens.capture.idle_detector_windows import (
        get_idle_seconds as get_idle_seconds,
    )
elif sys.platform == "darwin":
    from chronolens.capture.idle_detector_macos import (
        get_idle_seconds as get_idle_seconds,
    )
elif sys.platform.startswith("linux"):
    from chronolens.capture.idle_detector_linux import (
        get_idle_seconds as get_idle_seconds,
    )
else:  # pragma: no cover — exotic platform fallback

    def get_idle_seconds() -> float:
        """Return 0.0 on unsupported platforms."""
        return 0.0


__all__ = ["get_idle_seconds"]
