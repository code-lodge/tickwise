"""Process-wide runtime singletons.

Holds the long-lived `CaptureLoop` and `SessionTracker` so the tray icon,
the FastAPI status endpoint, and the main entrypoint all see the same
instances. Tests can call `set_capture_loop()` / `set_session_tracker()`
to inject doubles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chronolens.capture.loop import CaptureLoop
    from chronolens.sessions.tracker import SessionTracker


_capture_loop: CaptureLoop | None = None
_session_tracker: SessionTracker | None = None


def set_capture_loop(loop: CaptureLoop | None) -> None:
    global _capture_loop
    _capture_loop = loop


def get_capture_loop() -> CaptureLoop | None:
    return _capture_loop


def set_session_tracker(tracker: SessionTracker | None) -> None:
    global _session_tracker
    _session_tracker = tracker


def get_session_tracker() -> SessionTracker | None:
    return _session_tracker
