"""macOS implementation of idle-time detection.

Uses IOKit's HIDIdleTime registry property — the same source as
`ioreg -c IOHIDSystem`. Two paths:

1. Preferred: pyobjc's `Quartz.CGEventSourceSecondsSinceLastEventType`
   with `kCGAnyInputEventType` — clean and dependency-light.
2. Fallback: spawn `ioreg` and parse `HIDIdleTime` (nanoseconds).

If neither works we return 0.0 so the capture loop keeps running.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def _idle_via_quartz() -> float | None:
    try:
        from Quartz import (
            CGEventSourceSecondsSinceLastEventType,
            kCGAnyInputEventType,
            kCGEventSourceStateHIDSystemState,
        )
    except ImportError:
        return None
    try:
        secs = CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateHIDSystemState, kCGAnyInputEventType)
    except Exception:
        logger.debug("Quartz idle query failed", exc_info=True)
        return None
    return float(secs) if secs is not None else None


def _idle_via_ioreg() -> float | None:
    try:
        out = subprocess.run(  # noqa: S603,S607 — fixed argv, no shell
            ["ioreg", "-c", "IOHIDSystem"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    for line in out.stdout.splitlines():
        if "HIDIdleTime" in line:
            try:
                ns = int(line.rsplit("=", 1)[-1].strip())
                return ns / 1_000_000_000.0
            except (ValueError, IndexError):
                continue
    return None


def get_idle_seconds() -> float:
    """Seconds since last keyboard or mouse input on macOS, or 0.0 on failure."""
    for source in (_idle_via_quartz, _idle_via_ioreg):
        secs = source()
        if secs is not None and secs >= 0:
            return secs
    return 0.0
