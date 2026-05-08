"""Screenshot capture via the `mss` library.

Single- and multi-monitor support. Each tick captures every enabled
monitor (so a focus switch is instant — the screenshot is already in
memory) but only the focused monitor is sent to OCR + classification.

Screenshots are returned as raw BGRA byte buffers plus their geometry;
nothing is ever written to disk.
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
class MonitorInfo:
    """Geometry of a connected monitor.

    `index` is the position in `mss.monitors` (1-based; 0 is the virtual
    bounding box and we never persist it).
    """

    index: int
    left: int
    top: int
    width: int
    height: int

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.left + self.width and self.top <= y < self.top + self.height


@dataclass(frozen=True, slots=True)
class Screenshot:
    """A raw screenshot held in memory."""

    width: int
    height: int
    bgra: bytes
    monitor_index: int = 1


class ScreenCapturer:
    """Wrapper around `mss.mss()` that captures one or more monitors.

    Caches the `mss` instance so we don't pay re-initialisation cost on every
    capture. Use as a context manager or call `close()` explicitly.
    """

    def __init__(self) -> None:
        if not _MSS_AVAILABLE:
            raise RuntimeError("mss is not installed — install via `pip install mss`")
        self._sct: Any = mss.mss()

    def list_monitors(self) -> list[MonitorInfo]:
        """Return one MonitorInfo per physical display (virtual screen excluded)."""
        return [
            MonitorInfo(
                index=idx,
                left=int(m.get("left", 0)),
                top=int(m.get("top", 0)),
                width=int(m.get("width", 0)),
                height=int(m.get("height", 0)),
            )
            for idx, m in enumerate(self._sct.monitors)
            if idx >= 1
        ]

    def capture_primary(self) -> Screenshot:
        """Grab the primary monitor.

        `mss.monitors[0]` is the virtual screen spanning all displays;
        `monitors[1]` is the OS-designated primary.
        """
        return self.capture_monitor(1 if len(self._sct.monitors) > 1 else 0)

    def capture_monitor(self, index: int) -> Screenshot:
        """Grab a specific monitor by its `mss.monitors` index."""
        if index < 0 or index >= len(self._sct.monitors):
            raise IndexError(f"monitor index {index} out of range (have {len(self._sct.monitors)})")
        img = self._sct.grab(self._sct.monitors[index])
        return Screenshot(
            width=int(img.width),
            height=int(img.height),
            bgra=bytes(img.bgra),
            monitor_index=index,
        )

    def capture_all(self, indices: list[int] | None = None) -> dict[int, Screenshot]:
        """Capture every requested monitor (defaults to all physical displays).

        Returning a dict keyed by index keeps the focus-switch path simple:
        the loop already has the screenshot for the newly focused monitor.
        """
        if indices is None:
            indices = [m.index for m in self.list_monitors()]
        return {idx: self.capture_monitor(idx) for idx in indices}

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
