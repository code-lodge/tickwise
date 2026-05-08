"""FastAPI application factory for Tickwise."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tickwise import __version__, runtime
from tickwise.api.routes_backup import router as backup_router
from tickwise.api.routes_calendar import router as calendar_router
from tickwise.api.routes_categories import router as categories_router
from tickwise.api.routes_clients import router as clients_router
from tickwise.api.routes_cloudflare import router as cloudflare_router
from tickwise.api.routes_invoices import router as invoices_router
from tickwise.api.routes_llm import router as llm_router
from tickwise.api.routes_mobile import router as mobile_router
from tickwise.api.routes_monitors import router as monitors_router
from tickwise.api.routes_onboarding import router as onboarding_router
from tickwise.api.routes_pairing import router as pairing_router
from tickwise.api.routes_pomodoro import router as pomodoro_router
from tickwise.api.routes_profile import router as profile_router
from tickwise.api.routes_projects import router as projects_router
from tickwise.api.routes_redaction import router as redaction_router
from tickwise.api.routes_reports import router as reports_router
from tickwise.api.routes_sessions import router as sessions_router
from tickwise.api.routes_settings import router as settings_router
from tickwise.api.websocket import router as ws_router
from tickwise.config import API_HOST, API_PORT

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_PWA_BUNDLED_DIR = Path(__file__).resolve().parent / "static_mobile"
_PWA_SOURCE_DIR = Path(__file__).resolve().parent.parent / "mobile"

_start_time = time.time()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Initialises the database schema as a side effect so any embedding
    (uvicorn, gunicorn, the test client) gets a working DB without
    relying on `python -m tickwise` having run first. `init_db()` is
    idempotent — re-running it is a no-op.

    Returns:
        Configured FastAPI instance with all routers mounted.
    """
    from tickwise.db.schema import init_db

    init_db()

    app = FastAPI(
        title="Tickwise",
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
    app.include_router(pomodoro_router)
    app.include_router(pairing_router)
    app.include_router(mobile_router)
    app.include_router(monitors_router)
    app.include_router(onboarding_router)
    app.include_router(backup_router)
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
    _mount_pwa(app)
    return app


def _mount_static_dashboard(app: FastAPI) -> None:
    """Serve the built Angular dashboard from `tickwise/static/` if present.

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
                    "tickwise/static/, or use `ng serve --proxy-config proxy.conf.json`."
                ),
                "api_docs": "/api/docs",
            }


def _mount_pwa(app: FastAPI) -> None:
    """Mount the mobile PWA at /m/ if its assets are available.

    Tries the packaged location (`tickwise/static_mobile/`) first, then
    falls back to the source folder (`mobile/`) so `python -m tickwise`
    works straight from a clean checkout.
    """
    target = _PWA_BUNDLED_DIR if (_PWA_BUNDLED_DIR / "index.html").is_file() else _PWA_SOURCE_DIR
    if not (target / "index.html").is_file():
        return
    app.mount("/m", StaticFiles(directory=target, html=True), name="mobile-pwa")


# Module-level app instance used by uvicorn.
app = create_app()
