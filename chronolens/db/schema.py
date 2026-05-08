"""Database schema definition and migration framework."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

from chronolens.db.connection import get_connection

logger = logging.getLogger(__name__)

# Current schema version — bump when adding migrations.
SCHEMA_VERSION: int = 6

# ─── DDL ─────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    color       TEXT NOT NULL DEFAULT '#3B82F6',
    client_id   INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    hourly_rate REAL,
    currency    TEXT NOT NULL DEFAULT 'USD',
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS clients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT,
    timezone    TEXT NOT NULL DEFAULT 'UTC',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS task_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    color       TEXT NOT NULL DEFAULT '#6B7280',
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS activities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at     TEXT NOT NULL,
    window_title    TEXT,
    process_name    TEXT,
    app_name        TEXT,
    url             TEXT,
    ocr_text        TEXT,
    redacted_text   TEXT,
    phash           TEXT,
    privacy_level   INTEGER NOT NULL DEFAULT 2,
    change_detected INTEGER NOT NULL DEFAULT 0,
    source          TEXT NOT NULL DEFAULT 'pending_classification',
    project_id      INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    category_id     INTEGER REFERENCES task_categories(id) ON DELETE SET NULL,
    confidence      REAL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    duration_secs   INTEGER,
    project_id      INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    category_id     INTEGER REFERENCES task_categories(id) ON DELETE SET NULL,
    description     TEXT,
    tags            TEXT,
    is_manual       INTEGER NOT NULL DEFAULT 0,
    is_billed       INTEGER NOT NULL DEFAULT 0,
    invoice_id      INTEGER REFERENCES invoices(id) ON DELETE SET NULL,
    llm_classified  INTEGER NOT NULL DEFAULT 0,
    confidence      REAL,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS pomodoro_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    type            TEXT NOT NULL CHECK(type IN ('work', 'short_break', 'long_break')),
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    completed       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS invoices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    invoice_number  TEXT NOT NULL UNIQUE,
    issued_date     TEXT NOT NULL,
    due_date        TEXT,
    status          TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'sent', 'paid', 'overdue', 'cancelled')),
    subtotal        REAL NOT NULL DEFAULT 0,
    tax_rate        REAL NOT NULL DEFAULT 0,
    tax_amount      REAL NOT NULL DEFAULT 0,
    total           REAL NOT NULL DEFAULT 0,
    currency        TEXT NOT NULL DEFAULT 'USD',
    notes           TEXT,
    pdf_path        TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS invoice_line_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id      INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    session_id      INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    description     TEXT NOT NULL,
    hours           REAL NOT NULL DEFAULT 0,
    rate            REAL NOT NULL DEFAULT 0,
    amount          REAL NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS freelancer_profile (
    id              INTEGER PRIMARY KEY CHECK(id = 1),
    name            TEXT NOT NULL DEFAULT '',
    email           TEXT NOT NULL DEFAULT '',
    company         TEXT,
    address         TEXT,
    tax_id          TEXT,
    default_currency TEXT NOT NULL DEFAULT 'USD',
    default_hourly_rate REAL,
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    invoice_prefix  TEXT NOT NULL DEFAULT 'INV',
    invoice_next_number INTEGER NOT NULL DEFAULT 1,
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS calendar_providers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL CHECK(type IN ('caldav', 'google', 'ical')),
    url             TEXT,
    username        TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    last_synced_at  TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS sync_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id     INTEGER REFERENCES calendar_providers(id) ON DELETE CASCADE,
    synced_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    events_imported INTEGER NOT NULL DEFAULT 0,
    events_exported INTEGER NOT NULL DEFAULT 0,
    error           TEXT
);

CREATE TABLE IF NOT EXISTS cloudflare_config (
    id              INTEGER PRIMARY KEY CHECK(id = 1),
    tunnel_id       TEXT,
    tunnel_name     TEXT,
    hostname        TEXT,
    is_active       INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS ics_feed_config (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    token           TEXT NOT NULL UNIQUE,
    include_descriptions INTEGER NOT NULL DEFAULT 0,
    project_filter  TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS llm_config (
    id              INTEGER PRIMARY KEY CHECK(id = 1),
    provider        TEXT NOT NULL DEFAULT 'anthropic' CHECK(provider IN ('anthropic', 'openai')),
    model           TEXT NOT NULL DEFAULT 'claude-haiku-4-5-20251001',
    api_key_ref     TEXT,
    temperature     REAL NOT NULL DEFAULT 0.1,
    max_tokens      INTEGER NOT NULL DEFAULT 256,
    monthly_budget_cents INTEGER NOT NULL DEFAULT 0,
    monthly_spent_cents REAL NOT NULL DEFAULT 0,
    budget_reset_day INTEGER NOT NULL DEFAULT 1,
    is_active       INTEGER NOT NULL DEFAULT 1,
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS llm_usage_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt_tokens   INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd        REAL NOT NULL DEFAULT 0,
    cost_cents      REAL NOT NULL DEFAULT 0,
    latency_ms      INTEGER,
    cache_hit       INTEGER NOT NULL DEFAULT 0,
    classification_success INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS classification_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key       TEXT NOT NULL UNIQUE,
    project_id      INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    category_id     INTEGER REFERENCES task_categories(id) ON DELETE SET NULL,
    description     TEXT,
    confidence      REAL,
    llm_response    TEXT,
    hit_count       INTEGER NOT NULL DEFAULT 1,
    last_hit_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    expires_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_redaction_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern         TEXT NOT NULL,
    match_mode      TEXT NOT NULL DEFAULT 'contains' CHECK(match_mode IN ('contains', 'regex', 'exact')),
    replacement     TEXT NOT NULL DEFAULT '[REDACTED]',
    description     TEXT,
    is_regex        INTEGER NOT NULL DEFAULT 0,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS redaction_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER REFERENCES activities(id) ON DELETE CASCADE,
    privacy_level   INTEGER,
    original_length INTEGER,
    redacted_length INTEGER,
    redaction_count INTEGER NOT NULL DEFAULT 0,
    categories_hit  TEXT,
    rule_type       TEXT,
    match_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS mobile_auth_tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash  TEXT NOT NULL UNIQUE,
    device_name TEXT,
    last_used   TEXT,
    expires_at  TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_activities_captured_at ON activities(captured_at);
CREATE INDEX IF NOT EXISTS idx_activities_source ON activities(source);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_ended_at ON sessions(ended_at);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_classification_cache_key ON classification_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_classification_cache_expires ON classification_cache(expires_at);
"""


def init_db() -> None:
    """Create all tables and run pending migrations.

    Safe to call multiple times — uses CREATE IF NOT EXISTS throughout.
    """
    conn = get_connection()
    # Execute DDL statements individually so SQLite doesn't choke on the
    # multi-statement string in strict mode.
    for statement in _DDL.split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
    _apply_migrations(conn)
    logger.info("Database initialised (schema_version=%d)", SCHEMA_VERSION)


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply any pending schema migrations in order."""
    current = _current_version(conn)
    for version, migrate_fn in _MIGRATIONS:
        if version > current:
            logger.info("Applying migration %d", version)
            migrate_fn(conn)
            conn.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))
            conn.commit()


# ─── Migration registry ───────────────────────────────────────────────────────
# Each entry: (version_number, callable(conn) -> None)


def _migration_001_seed_defaults(conn: sqlite3.Connection) -> None:
    """Seed default settings and singleton rows on first run."""
    from chronolens.config import DEFAULTS

    for key, value in DEFAULTS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
            (key, str(value).lower() if isinstance(value, bool) else str(value)),
        )
    conn.execute("INSERT OR IGNORE INTO freelancer_profile(id) VALUES (1)")
    conn.execute("INSERT OR IGNORE INTO llm_config(id) VALUES (1)")
    conn.execute("INSERT OR IGNORE INTO cloudflare_config(id) VALUES (1)")


def _migration_002_add_activity_source(conn: sqlite3.Connection) -> None:
    """Add `source` column to activities for tracking classification state.

    Idempotent — only adds the column if it doesn't already exist.
    """
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(activities)")}
    if "source" not in cols:
        conn.execute("ALTER TABLE activities ADD COLUMN source TEXT NOT NULL DEFAULT 'pending_classification'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_source ON activities(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_ended_at ON sessions(ended_at)")


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Idempotently add a column to a table; no-op if it already exists."""
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _migration_003_classification_columns(conn: sqlite3.Connection) -> None:
    """Phase 3 — extend tables for the LLM classification pipeline."""
    # activities → carries the per-tick classification result.
    _add_column_if_missing(
        conn, "activities", "project_id", "project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL"
    )
    _add_column_if_missing(
        conn,
        "activities",
        "category_id",
        "category_id INTEGER REFERENCES task_categories(id) ON DELETE SET NULL",
    )
    _add_column_if_missing(conn, "activities", "confidence", "confidence REAL")

    # llm_config → budget tracking + activation.
    _add_column_if_missing(
        conn, "llm_config", "monthly_budget_cents", "monthly_budget_cents INTEGER NOT NULL DEFAULT 0"
    )
    _add_column_if_missing(conn, "llm_config", "monthly_spent_cents", "monthly_spent_cents REAL NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "llm_config", "budget_reset_day", "budget_reset_day INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(conn, "llm_config", "is_active", "is_active INTEGER NOT NULL DEFAULT 1")

    # llm_usage_log → cache + outcome tracking.
    _add_column_if_missing(conn, "llm_usage_log", "cost_cents", "cost_cents REAL NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "llm_usage_log", "cache_hit", "cache_hit INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(
        conn,
        "llm_usage_log",
        "classification_success",
        "classification_success INTEGER NOT NULL DEFAULT 1",
    )

    # classification_cache → hit tracking + raw response for debug.
    _add_column_if_missing(conn, "classification_cache", "llm_response", "llm_response TEXT")
    _add_column_if_missing(conn, "classification_cache", "hit_count", "hit_count INTEGER NOT NULL DEFAULT 1")
    _add_column_if_missing(
        conn,
        "classification_cache",
        "last_hit_at",
        "last_hit_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))",
    )

    # custom_redaction_rules → match_mode + description.
    _add_column_if_missing(
        conn,
        "custom_redaction_rules",
        "match_mode",
        "match_mode TEXT NOT NULL DEFAULT 'contains'",
    )
    _add_column_if_missing(conn, "custom_redaction_rules", "description", "description TEXT")

    # redaction_log → richer transparency stats.
    _add_column_if_missing(conn, "redaction_log", "privacy_level", "privacy_level INTEGER")
    _add_column_if_missing(conn, "redaction_log", "original_length", "original_length INTEGER")
    _add_column_if_missing(conn, "redaction_log", "redacted_length", "redacted_length INTEGER")
    _add_column_if_missing(conn, "redaction_log", "redaction_count", "redaction_count INTEGER NOT NULL DEFAULT 0")
    _add_column_if_missing(conn, "redaction_log", "categories_hit", "categories_hit TEXT")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_project_id ON activities(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_log_created_at ON llm_usage_log(created_at)")


def _migration_004_invoicing(conn: sqlite3.Connection) -> None:
    """Phase 6 — extend profile + invoices for full invoicing lifecycle."""
    # Freelancer profile additions: bank details, logo, defaults.
    _add_column_if_missing(conn, "freelancer_profile", "iban", "iban TEXT")
    _add_column_if_missing(conn, "freelancer_profile", "bank_name", "bank_name TEXT")
    _add_column_if_missing(conn, "freelancer_profile", "logo_path", "logo_path TEXT")
    _add_column_if_missing(
        conn,
        "freelancer_profile",
        "invoice_default_due_days",
        "invoice_default_due_days INTEGER NOT NULL DEFAULT 14",
    )
    _add_column_if_missing(
        conn,
        "freelancer_profile",
        "invoice_default_tax_rate",
        "invoice_default_tax_rate REAL NOT NULL DEFAULT 21.0",
    )
    _add_column_if_missing(conn, "freelancer_profile", "payment_terms", "payment_terms TEXT")

    # Invoice lifecycle timestamps.
    _add_column_if_missing(conn, "invoices", "sent_at", "sent_at TEXT")
    _add_column_if_missing(conn, "invoices", "paid_at", "paid_at TEXT")
    _add_column_if_missing(conn, "invoices", "project_id", "project_id INTEGER")

    # Client billing extras.
    _add_column_if_missing(conn, "clients", "address", "address TEXT")
    _add_column_if_missing(conn, "clients", "tax_id", "tax_id TEXT")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id)")


def _migration_005_pomodoro(conn: sqlite3.Connection) -> None:
    """Phase 7 — let activities reference the active pomodoro period."""
    _add_column_if_missing(
        conn,
        "activities",
        "pomodoro_session_id",
        "pomodoro_session_id INTEGER REFERENCES pomodoro_sessions(id) ON DELETE SET NULL",
    )
    _add_column_if_missing(
        conn,
        "sessions",
        "pomodoro_count",
        "pomodoro_count INTEGER NOT NULL DEFAULT 0",
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_started_at " "ON pomodoro_sessions(started_at)")


def _migration_006_multi_monitor(conn: sqlite3.Connection) -> None:
    """Phase 10 — record which monitor each activity was captured from."""
    _add_column_if_missing(
        conn,
        "activities",
        "monitor_index",
        "monitor_index INTEGER NOT NULL DEFAULT 1",
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitor_preferences (
            monitor_index INTEGER PRIMARY KEY,
            label         TEXT,
            enabled       INTEGER NOT NULL DEFAULT 1,
            is_primary    INTEGER NOT NULL DEFAULT 0,
            updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
        """)


_MIGRATIONS: list[tuple[int, Callable[[sqlite3.Connection], None]]] = [
    (1, _migration_001_seed_defaults),
    (2, _migration_002_add_activity_source),
    (3, _migration_003_classification_columns),
    (4, _migration_004_invoicing),
    (5, _migration_005_pomodoro),
    (6, _migration_006_multi_monitor),
]
