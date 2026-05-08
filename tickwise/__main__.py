"""Entry point: python -m tickwise"""

from __future__ import annotations

import logging
import os
import sys
import threading

# When packaged with PyInstaller --windowed, sys.stdout/stderr are None.
# uvicorn's DefaultFormatter calls sys.stdout.isatty() at import time and
# crashes. Wire stdio to the per-user log file before importing uvicorn.
if sys.stdout is None or sys.stderr is None:
    _log_dir = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.tickwise"), "Tickwise")
    os.makedirs(_log_dir, exist_ok=True)
    _log_path = os.path.join(_log_dir, "tickwise.log")
    _log_file = open(_log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = _log_file
    sys.stderr = _log_file

import uvicorn  # noqa: E402

from tickwise import runtime  # noqa: E402
from tickwise.capture.loop import CaptureLoop  # noqa: E402
from tickwise.classification.pipeline import ClassificationWorker  # noqa: E402
from tickwise.config import API_HOST, API_PORT  # noqa: E402
from tickwise.db.schema import init_db  # noqa: E402
from tickwise.pomodoro.timer import PomodoroTimer  # noqa: E402
from tickwise.sessions.tracker import SessionTracker  # noqa: E402
from tickwise.tray import run_tray  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_shutdown_event = threading.Event()


def _start_api_server() -> threading.Thread:
    config = uvicorn.Config(
        "tickwise.app:app",
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        loop="asyncio",
        log_config=None,
    )
    server = uvicorn.Server(config)

    def _run() -> None:
        server.run()
        _shutdown_event.set()

    t = threading.Thread(target=_run, name="api-server", daemon=True)
    t.start()
    return t


def main() -> None:
    """Initialise the DB, start API + capture loop, then enter the tray loop."""
    logger.info("Tickwise starting up")
    init_db()

    tracker = SessionTracker()
    runtime.set_session_tracker(tracker)

    loop = CaptureLoop(
        on_session_extend=tracker.extend,
        on_session_change=tracker.on_change,
    )
    runtime.set_capture_loop(loop)
    loop.start()

    classifier = ClassificationWorker()
    classifier.start()

    pomodoro = PomodoroTimer()
    runtime.set_pomodoro_timer(pomodoro)
    pomodoro.start_thread()

    _start_api_server()
    logger.info("API server starting on http://%s:%d", API_HOST, API_PORT)

    def on_quit() -> None:
        logger.info("Quit requested — shutting down")
        loop.stop()
        classifier.stop()
        pomodoro.stop_thread()
        tracker.flush()
        _shutdown_event.set()

    run_tray(on_quit)
    _shutdown_event.wait()
    logger.info("Tickwise stopped")


if __name__ == "__main__":
    main()
