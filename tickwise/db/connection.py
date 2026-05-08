"""Thread-local SQLite connection management with WAL mode and FK enforcement."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from tickwise.config import db_path

_local = threading.local()
_db_path_override: Path | None = None


def set_db_path(path: Path | None) -> None:
    """Override the database path (used in tests). Pass None to clear the override."""
    global _db_path_override
    _db_path_override = path
    # Clear any cached connections so the next call uses the new path.
    if hasattr(_local, "connection"):
        with suppress(Exception):
            _local.connection.close()
        del _local.connection


def _effective_db_path() -> Path:
    return _db_path_override if _db_path_override is not None else db_path()


def get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating it on first access.

    The connection is configured with:
    - WAL journal mode for concurrent read access.
    - Foreign key enforcement enabled.
    - Row factory set to sqlite3.Row for dict-like access.

    Returns:
        An open sqlite3.Connection bound to the current thread.
    """
    if not hasattr(_local, "connection"):
        path = _effective_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.connection = conn
    conn_: sqlite3.Connection = _local.connection
    return conn_


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Context manager that yields a connection inside an explicit transaction.

    Commits on clean exit, rolls back on exception.

    Yields:
        The thread-local sqlite3.Connection.

    Raises:
        Exception: Re-raises any exception that occurs within the block.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def close_connection() -> None:
    """Close and remove the thread-local connection (call from thread teardown)."""
    if hasattr(_local, "connection"):
        _local.connection.close()
        del _local.connection
