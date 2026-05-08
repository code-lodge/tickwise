"""Screenshot capture via the `mss` library.

Captures the primary monitor only in Phase 1; multi-monitor support is added
in Phase 10. Screenshots are returned as raw BGRA byte buffers plus their
size, never written to disk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    import mss

    _MSS_AVAILABLE = True
except ImportError:
    _MSS_AVAILABLE = False


@dataclass(frozen=True, slots=True)
class Screenshot:
    """A raw screenshot held in memory."""

    width: int
    height: int
    bgra: bytes


class ScreenCapturer:
    """Wrapper around `mss.mss()` that grabs the primary monitor each tick.

    Caches the `mss` instance so we don't pay re-initialisation cost on every
    capture. Use as a context manager or call `close()` explicitly.
    """

    def __init__(self) -> None:
        if not _MSS_AVAILABLE:
            raise RuntimeError("mss is not installed — install via `pip install mss`")
        self._sct: Any = mss.mss()

    def capture_primary(self) -> Screenshot:
        """Grab the primary monitor.

        `mss.monitors[0]` is the virtual screen spanning all displays;
        `monitors[1]` is the OS-designated primary.
        """
        monitor = self._sct.monitors[1] if len(self._sct.monitors) > 1 else self._sct.monitors[0]
        img = self._sct.grab(monitor)
        return Screenshot(width=int(img.width), height=int(img.height), bgra=bytes(img.bgra))

    def close(self) -> None:
        """Release the underlying `mss` resources."""
        with _suppress():
            self._sct.close()

    def __enter__(self) -> ScreenCapturer:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class _suppress:
    """Tiny suppression helper to keep imports lean."""

    def __enter__(self) -> _suppress:
        return self

    def __exit__(self, exc_type: object, *_rest: object) -> bool:
        return exc_type is not None
