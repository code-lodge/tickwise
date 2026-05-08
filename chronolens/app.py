"""FastAPI application factory for ChronoLens."""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chronolens import __version__, runtime
from chronolens.api.routes_sessions import router as sessions_router
from chronolens.api.routes_settings import router as settings_router
from chronolens.api.websocket import router as ws_router
from chronolens.config import API_HOST, API_PORT

_start_time = time.time()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with all routers mounted.
    """
    app = FastAPI(
        title="ChronoLens",
        version=__version__,
        description="Privacy-conscious automatic time tracking API",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Allow the Angular dev server and the local dashboard to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://{API_HOST}:{API_PORT}",
            "http://localhost:4200",  # Angular dev server
            "http://127.0.0.1:4200",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(settings_router)
    app.include_router(sessions_router)
    app.include_router(ws_router)

    @app.get("/api/status", tags=["meta"])
    async def status() -> dict[str, Any]:
        """Health-check endpoint.

        Returns:
            Dict with status, version, uptime_secs, and tracking state.
        """
        loop = runtime.get_capture_loop()
        tracking = bool(loop and loop.is_running and not loop.is_paused)
        return {
            "status": "ok",
            "version": __version__,
            "uptime_secs": int(time.time() - _start_time),
            "tracking": tracking,
        }

    return app


# Module-level app instance used by uvicorn.
app = create_app()
