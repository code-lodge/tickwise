"""The 1 Hz capture loop.

Runs in its own daemon thread. Each tick:

1. Sample idle time; if past `idle_split_threshold`, skip the tick.
2. Sample active window title + process.
3. Capture the primary monitor.
4. Run change detection (title/process/url fast path, then phash).
5. On change → run OCR, persist an `activities` row, push to classification
   queue, and notify the session tracker.
6. On no change → call `extend_current_session()` so an open session keeps
   accumulating duration.

The loop is resilient to per-tick failures: any exception is logged and the
loop sleeps until the next tick. Pause/resume is controlled via
`set_paused(bool)` which is checked at the top of each tick.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

from tickwise.capture.change_detector import ChangeState, detect_change
from tickwise.capture.idle_detector import get_idle_seconds
from tickwise.capture.screenshot import MonitorInfo, ScreenCapturer, Screenshot
from tickwise.capture.window_info import WindowInfo, get_active_window, get_window_center
from tickwise.classification.queue import ClassificationJob, submit
from tickwise.config import DEFAULTS
from tickwise.db.connection import transaction
from tickwise.ocr.extractor import extract_text

logger = logging.getLogger(__name__)


class CaptureLoop:
    """Owns the capture thread and its mutable state."""

    def __init__(
        self,
        *,
        tick_seconds: float = 1.0,
        idle_split_threshold: float | None = None,
        phash_threshold: int | None = None,
        ocr_downscale_width: int | None = None,
        ocr_runner: Callable[[Screenshot, int], str] | None = None,
        on_session_extend: Callable[[WindowInfo, datetime], None] | None = None,
        on_session_change: Callable[..., None] | None = None,
    ) -> None:
        self._tick_seconds = tick_seconds
        self._idle_split = (
            float(idle_split_threshold)
            if idle_split_threshold is not None
            else float(cast(int, DEFAULTS["idle_split_threshold"]))
        )
        self._phash_threshold = (
            int(phash_threshold) if phash_threshold is not None else int(cast(int, DEFAULTS["phash_change_threshold"]))
        )
        self._ocr_width = (
            int(ocr_downscale_width)
            if ocr_downscale_width is not None
            else int(cast(int, DEFAULTS["ocr_downscale_width"]))
        )
        self._ocr_runner = ocr_runner or (lambda shot, width: extract_text(shot, downscale_width=width))
        self._on_extend = on_session_extend
        self._on_change = on_session_change
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None
        # One change-state per monitor index so a focus switch picks up
        # exactly where it left off.
        self._states: dict[int, ChangeState] = {}
        self._capturer: ScreenCapturer | None = None
        self._last_focused_index: int = 1
        self.tick_count = 0
        self.last_window: WindowInfo = WindowInfo(title="", process_name="", pid=None)
        self.last_idle_seconds: float = 0.0

    # ─── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Spawn the capture thread (no-op if already running)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="capture-loop", daemon=True)
        self._thread.start()
        logger.info("Capture loop started (tick=%.2fs)", self._tick_seconds)

    def stop(self, join_timeout: float = 5.0) -> None:
        """Signal the thread to stop and wait briefly for it to exit."""
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=join_timeout)
        if self._capturer is not None:
            self._capturer.close()
            self._capturer = None
        logger.info("Capture loop stopped")

    def pause(self) -> None:
        self._paused.set()
        logger.info("Capture loop paused")

    def resume(self) -> None:
        self._paused.clear()
        logger.info("Capture loop resumed")

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ─── core tick ────────────────────────────────────────────────────────

    def tick_once(self) -> bool:
        """Run a single tick synchronously. Returns True if a change was detected.

        Exposed primarily for tests — the main loop calls this in a thread.
        """
        self.tick_count += 1
        now = datetime.now(UTC)

        idle = get_idle_seconds()
        self.last_idle_seconds = idle
        if idle >= self._idle_split:
            logger.debug("idle=%.1fs above split threshold, skipping tick", idle)
            return False

        window = get_active_window()
        self.last_window = window

        shots = self._safe_capture_all()
        if not shots:
            return False

        focused_index = self._pick_focused_monitor(shots)
        self._refresh_secondary_hashes(shots, focused_index)
        focus_changed = focused_index != self._last_focused_index
        self._last_focused_index = focused_index

        screenshot = shots.get(focused_index)
        from tickwise.capture import browser_bridge

        browser_ctx = browser_bridge.latest()
        url_for_change = browser_ctx.url if browser_ctx and browser_ctx.url else ""
        state = self._states.setdefault(focused_index, ChangeState())
        result = detect_change(
            screenshot,
            window.title,
            window.process_name,
            url=url_for_change,
            state=state,
            phash_threshold=self._phash_threshold,
        )

        # A focus switch onto a different monitor counts as a change even
        # if the screen contents on that monitor haven't changed since last
        # we saw it — the *focus* moved.
        if focus_changed and not result.changed:
            result = detect_change(
                screenshot,
                window.title,
                window.process_name,
                url=url_for_change,
                state=state,
                phash_threshold=self._phash_threshold,
            )

        if not result.changed and not focus_changed:
            logger.debug("no change, skipping OCR")
            if self._on_extend is not None:
                self._on_extend(window, now)
            return False

        ocr_text = ""
        if screenshot is not None:
            ocr_text = self._ocr_runner(screenshot, self._ocr_width)

        activity_id = self._persist_activity(window, ocr_text, result.phash, now, focused_index)
        submit(
            ClassificationJob(
                activity_id=activity_id or 0,
                captured_at=now,
                window_title=window.title,
                process_name=window.process_name,
                raw_ocr_text=ocr_text,
                redacted_text=ocr_text,  # redaction applied in Phase 3 wiring
                phash=result.phash,
            )
        )
        if self._on_change is not None:
            try:
                self._on_change(window, now, ocr_text)
            except TypeError:
                # Back-compat for callbacks that haven't grown the
                # ocr_text parameter yet (older tests, future stubs).
                self._on_change(window, now)
        return True

    def _pick_focused_monitor(self, shots: dict[int, Screenshot]) -> int:
        """Return the monitor index covering the active window's centre.

        Falls back to the previously-focused monitor (or the lowest available
        index) when the platform can't tell us where the window is.
        """
        if len(shots) == 1:
            return next(iter(shots))
        center = get_window_center()
        if center is not None and self._capturer is not None:
            for monitor in self._capturer.list_monitors():
                if monitor.index in shots and monitor.contains(*center):
                    return monitor.index
        if self._last_focused_index in shots:
            return self._last_focused_index
        return min(shots)

    def _refresh_secondary_hashes(self, shots: dict[int, Screenshot], focused_index: int) -> None:
        """Run change detection against non-focused monitors so their state stays
        warm — we don't OCR them, but we want the next focus switch to land on a
        fresh phash instead of comparing against stale data.
        """
        for idx, shot in shots.items():
            if idx == focused_index:
                continue
            state = self._states.setdefault(idx, ChangeState())
            detect_change(
                shot,
                "",
                "",
                url="",
                state=state,
                phash_threshold=self._phash_threshold,
            )

    # ─── internals ────────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            self._capturer = ScreenCapturer()
        except RuntimeError as exc:
            logger.warning("ScreenCapturer unavailable: %s — capture loop exiting", exc)
            return
        while not self._stop.is_set():
            if not self._paused.is_set():
                try:
                    self.tick_once()
                except Exception:
                    logger.exception("capture tick failed")
            self._wake.wait(self._tick_seconds)
            self._wake.clear()

    def _safe_capture(self) -> Screenshot | None:
        if self._capturer is None:
            try:
                self._capturer = ScreenCapturer()
            except RuntimeError:
                return None
        try:
            return self._capturer.capture_primary()
        except Exception:
            logger.exception("screenshot capture failed")
            return None

    def _safe_capture_all(self) -> dict[int, Screenshot]:
        if self._capturer is None:
            try:
                self._capturer = ScreenCapturer()
            except RuntimeError:
                return {}
        try:
            indices = _enabled_monitor_indices(self._capturer.list_monitors())
            return self._capturer.capture_all(indices or None)
        except Exception:
            logger.exception("multi-monitor capture failed")
            return {}

    def _persist_activity(
        self,
        window: WindowInfo,
        ocr_text: str,
        phash: str,
        captured_at: datetime,
        monitor_index: int = 1,
    ) -> int | None:
        # 1500 chars — enough for retrospective reclassification to find
        # keywords that don't always land in the first paragraph (e.g.
        # "sceneryenzo" appearing in a Shopify breadcrumb halfway down
        # the screenshot), bounded so the table stays cheap.
        snippet = ocr_text[:1500] if ocr_text else None
        from tickwise import runtime

        timer = runtime.get_pomodoro_timer()
        pomodoro_session_id = timer.current_focus_session_id() if timer else None
        try:
            with transaction() as conn:
                cur = conn.execute(
                    """
                    INSERT INTO activities
                        (captured_at, window_title, process_name, ocr_text,
                         redacted_text, phash, change_detected, source,
                         pomodoro_session_id, monitor_index)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 'unclassified', ?, ?)
                    """,
                    (
                        captured_at.isoformat(),
                        window.title or None,
                        window.process_name or None,
                        snippet,
                        snippet,
                        phash or None,
                        pomodoro_session_id,
                        monitor_index,
                    ),
                )
                lastrow = cur.lastrowid
            return int(lastrow) if lastrow is not None else None
        except Exception:
            logger.exception("failed to persist activity")
            return None


def _enabled_monitor_indices(detected: list[MonitorInfo]) -> list[int]:
    """Filter the detected monitor list against `monitor_preferences`.

    Returns an empty list when *no* monitors are explicitly enabled (treat as
    'all enabled'); otherwise returns the intersection. Detected monitors not
    present in preferences are kept by default — new hardware should not stay
    invisible until the user clicks something.
    """
    try:
        from tickwise.db.connection import get_connection

        prefs = {
            int(r["monitor_index"]): bool(r["enabled"])
            for r in get_connection().execute("SELECT monitor_index, enabled FROM monitor_preferences").fetchall()
        }
    except Exception:
        return [m.index for m in detected]
    if not prefs:
        return [m.index for m in detected]
    return [m.index for m in detected if prefs.get(m.index, True)]
