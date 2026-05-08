"""Shared pytest fixtures for ChronoLens test suite."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chronolens.db import connection as db_connection
from chronolens.db.schema import init_db


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a fresh in-memory-like SQLite database for each test.

    Sets the global DB path override to a temp file, initialises the schema,
    and tears it down after the test.

    Yields:
        Path to the temporary database file.
    """
    db_file = tmp_path / "test_chronolens.db"
    db_connection.set_db_path(db_file)
    init_db()
    yield db_file
    db_connection.close_connection()
    db_connection.set_db_path(None)


@pytest.fixture()
def client(tmp_db: Path) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient backed by the temp DB.

    Yields:
        httpx-compatible TestClient for the ChronoLens FastAPI app.
    """
    from chronolens.app import create_app

    app = create_app()
    with TestClient(app) as tc:
        yield tc
