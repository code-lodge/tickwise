"""Entry point: python -m chronolens"""

from __future__ import annotations

import logging
import threading

import uvicorn

from chronolens.config import API_HOST, API_PORT
from chronolens.db.schema import init_db
from chronolens.tray import run_tray

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_shutdown_event = threading.Event()


def _start_api_server() -> threading.Thread:
    config = uvicorn.Config(
        "chronolens.app:app",
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    def _run() -> None:
        server.run()
        _shutdown_event.set()

    t = threading.Thread(target=_run, name="api-server", daemon=True)
    t.start()
    return t


def main() -> None:
    """Initialise the database, start the API server, then enter the tray loop."""
    logger.info("ChronoLens starting up")
    init_db()

    _start_api_server()
    logger.info("API server starting on http://%s:%d", API_HOST, API_PORT)

    def on_quit() -> None:
        logger.info("Quit requested — shutting down")
        _shutdown_event.set()

    run_tray(on_quit)
    _shutdown_event.wait()
    logger.info("ChronoLens stopped")


if __name__ == "__main__":
    main()
