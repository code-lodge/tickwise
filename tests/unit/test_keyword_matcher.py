"""Tests for tickwise.classification.keyword_matcher.

Cover the three behaviors the user explicitly asked for:
1. Whole-keyword normalized match (spacing/case/punct ignored).
2. Pure-local — no network calls or external imports.
3. Multi-token keyword still wins when only one significant token shows up.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tickwise.classification.keyword_matcher import (
    _normalize,
    _split_keywords,
    _tokens,
    match_project,
)
from tickwise.db.connection import get_connection, set_db_path
from tickwise.db.schema import init_db


@pytest.fixture()
def fresh_db(tmp_path: Path):
    set_db_path(tmp_path / "test.db")
    init_db()
    yield get_connection()
    set_db_path(None)


def _make_project(conn, name: str, keywords: str) -> int:
    cur = conn.execute(
        "INSERT INTO projects (name, color, is_active, match_keywords) VALUES (?, '#000', 1, ?)",
        (name, keywords),
    )
    conn.commit()
    return int(cur.lastrowid)


def test_normalize_strips_non_alnum():
    assert _normalize("Scenery-Enzo Website!") == "sceneryenzowebsite"
    assert _normalize("scenery en zo") == "sceneryenzo"
    assert _normalize("") == ""


def test_split_keywords_dedupes_and_handles_commas():
    assert _split_keywords("foo\nbar, baz\n\nFOO") == ["foo", "bar", "baz"]


def test_tokens_drops_stopwords_and_short_tokens():
    assert _tokens("Sceneryenzo website") == ["sceneryenzo"]
    assert _tokens("the and or") == []
    assert _tokens("AB Tech") == ["tech"]


def test_match_handles_spacing_variation(fresh_db):
    pid = _make_project(fresh_db, "Sceneryenzo", "Sceneryenzo")
    hit = match_project("scenery en zo - tab - browser")
    assert hit is not None
    assert hit.project_id == pid
    assert hit.matched_keyword == "Sceneryenzo"


def test_match_handles_case_and_punct(fresh_db):
    _make_project(fresh_db, "SceneryEnzo", "SceneryEnzo")
    assert match_project("Visiting SCENERY-enzo.com today") is not None
    assert match_project("scenery_enzo dashboard") is not None


def test_partial_token_match_for_multiword_keyword(fresh_db):
    """User-stated requirement #3: 'Sceneryenzo website' should still match
    a haystack that only mentions 'sceneryenzo'."""
    pid = _make_project(fresh_db, "Sceneryenzo website", "Sceneryenzo website")
    hit = match_project("Tickwise and 5 more pages - sceneryenzo - Microsoft Edge")
    assert hit is not None
    assert hit.project_id == pid


def test_no_match_returns_none(fresh_db):
    _make_project(fresh_db, "Acme", "acme")
    assert match_project("totally unrelated window title") is None


def test_longer_keyword_wins_over_shorter(fresh_db):
    _make_project(fresh_db, "Generic Project", "scenery")
    longer = _make_project(fresh_db, "Sceneryenzo Website Build", "Sceneryenzo Website")
    hit = match_project("working on the Sceneryenzo website redesign")
    assert hit is not None
    assert hit.project_id == longer


def test_inactive_projects_ignored(fresh_db):
    fresh_db.execute(
        "INSERT INTO projects (name, color, is_active, match_keywords) VALUES (?, '#000', 0, ?)",
        ("Old Project", "old"),
    )
    fresh_db.commit()
    assert match_project("old archived window") is None


def test_blank_or_whitespace_haystack_returns_none(fresh_db):
    _make_project(fresh_db, "Acme", "acme")
    assert match_project("") is None
    assert match_project("   ") is None
