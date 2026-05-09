"""Integration tests for the static-dashboard mount and dev fallback."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestDevFallback:
    def test_root_returns_dev_pointer_when_no_static(self, tmp_path: Path) -> None:
        # Don't depend on whether the dev workstation has run `ng build`
        # — point the app at an empty directory and verify the fallback.
        from tickwise import app as app_module
        from tickwise.app import create_app

        original = app_module._STATIC_DIR
        try:
            app_module._STATIC_DIR = tmp_path / "static-empty"  # type: ignore[misc]
            app = create_app()
            with TestClient(app) as tc:
                r = tc.get("/")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "dev"
            assert body["api_docs"] == "/api/docs"
        finally:
            app_module._STATIC_DIR = original  # type: ignore[misc]


@pytest.mark.integration
class TestStaticServing:
    def test_static_index_served_when_built(self, tmp_path: Path) -> None:
        # Build a fake `static/` directory and instantiate a fresh app pointing at it.
        static = tmp_path / "static"
        static.mkdir()
        (static / "index.html").write_text("<html>built</html>", encoding="utf-8")
        (static / "main.js").write_text("console.log('hi');", encoding="utf-8")

        from tickwise import app as app_module
        from tickwise.app import create_app

        original = app_module._STATIC_DIR
        try:
            app_module._STATIC_DIR = static  # type: ignore[misc]
            app = create_app()
            with TestClient(app) as tc:
                root = tc.get("/")
                assert root.status_code == 200
                assert "built" in root.text
                # SPA fallback: unknown path → index.html.
                fallback = tc.get("/timeline")
                assert "built" in fallback.text
                # Real static asset is served.
                main = tc.get("/main.js")
                assert main.status_code == 200
                assert "console.log" in main.text
        finally:
            app_module._STATIC_DIR = original  # type: ignore[misc]
