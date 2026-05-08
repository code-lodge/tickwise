"""FastAPI application factory for ChronoLens."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from chronolens import __version__, runtime
from chronolens.api.routes_calendar import router as calendar_router
from chronolens.api.routes_categories import router as categories_router
from chronolens.api.routes_clients import router as clients_router
from chronolens.api.routes_cloudflare import router as cloudflare_router
from chronolens.api.routes_invoices import router as invoices_router
from chronolens.api.routes_llm import router as llm_router
from chronolens.api.routes_profile import router as profile_router
from chronolens.api.routes_projects import router as projects_router
from chronolens.api.routes_redaction import router as redaction_router
from chronolens.api.routes_reports import router as reports_router
from chronolens.api.routes_sessions import router as sessions_router
from chronolens.api.routes_settings import router as settings_router
from chronolens.api.websocket import router as ws_router
from chronolens.config import API_HOST, API_PORT

_STATIC_DIR = Path(__file__).resolve().parent / "static"

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
    app.include_router(projects_router)
    app.include_router(clients_router)
    app.include_router(categories_router)
    app.include_router(sessions_router)
    app.include_router(redaction_router)
    app.include_router(llm_router)
    app.include_router(calendar_router)
    app.include_router(cloudflare_router)
    app.include_router(reports_router)
    app.include_router(profile_router)
    app.include_router(invoices_router)
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

    _mount_static_dashboard(app)
    return app


def _mount_static_dashboard(app: FastAPI) -> None:
    """Serve the built Angular dashboard from `chronolens/static/` if present.

    Falls back to a placeholder JSON response on `/` when the production
    bundle isn't installed (development mode where Angular is served by
    `ng serve` on :4200 with a proxy to this API).
    """
    if _STATIC_DIR.is_dir() and (_STATIC_DIR / "index.html").is_file():
        app.mount(
            "/static",
            StaticFiles(directory=_STATIC_DIR, html=False),
            name="static-assets",
        )

        @app.get("/", include_in_schema=False)
        async def root() -> FileResponse:
            return FileResponse(_STATIC_DIR / "index.html")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa_fallback(path: str) -> FileResponse:
            target = _STATIC_DIR / path
            if target.is_file():
                return FileResponse(target)
            # Angular routing falls back to index.html for unknown client routes.
            return FileResponse(_STATIC_DIR / "index.html")

    else:

        @app.get("/", include_in_schema=False)
        async def dev_root() -> dict[str, Any]:
            return {
                "status": "dev",
                "message": (
                    "Dashboard not built. Run `ng build` from /dashboard to populate "
                    "chronolens/static/, or use `ng serve --proxy-config proxy.conf.json`."
                ),
                "api_docs": "/api/docs",
            }


# Module-level app instance used by uvicorn.
app = create_app()
