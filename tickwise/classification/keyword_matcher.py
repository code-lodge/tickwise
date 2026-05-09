"""Free, deterministic project classification by fuzzy keyword match.

100% local — no LLM, no API calls. Two-stage match:

1. Normalized substring: strip every non-alphanumeric character (and
   lowercase) from BOTH the keyword and the haystack, then substring
   match. Handles spacing, punctuation, and casing variation —
   "Sceneryenzo" matches "scenery en zo", "Scenery-Enzo", "SCENERY ENZO".

2. Token-set fallback: if the whole-keyword pass misses, split the
   keyword into significant words (stop-words and tiny tokens dropped)
   and require at least one of them to appear in the normalized
   haystack. This lets "Sceneryenzo website" still claim a window whose
   title only mentions "sceneryenzo".

When multiple projects could match, the project with the highest score
wins (score = total characters of matched text, with a 2× bonus for
whole-keyword matches over partial token matches).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from tickwise.db.connection import get_connection

logger = logging.getLogger(__name__)


# Generic words that don't identify a specific project — filtered when we
# fall back to per-token matching so they don't trigger spurious matches.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "the", "and", "or", "of", "for", "to", "a", "an", "in", "on", "with", "by", "at",
        "website", "site", "app", "page", "pages", "blog", "store", "dashboard", "admin",
        "project", "client", "work", "home", "main", "new", "old", "test", "dev",
        "staging", "prod", "production", "demo", "tab", "tabs", "window", "windows",
        "google", "chrome", "edge", "firefox", "safari",
    }
)

_MIN_TOKEN_LEN = 3
_MIN_NORMALIZED_LEN = 4
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(slots=True, frozen=True)
class KeywordMatch:
    project_id: int
    project_name: str
    matched_keyword: str
    score: int


def _normalize(text: str) -> str:
    """Lowercase and strip everything that isn't a letter or digit."""
    return "".join(c.lower() for c in text if c.isalnum())


def _split_keywords(blob: str | None) -> list[str]:
    """Split the per-project keyword blob into trimmed, deduplicated lines."""
    if not blob:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for raw in blob.replace(",", "\n").splitlines():
        kw = raw.strip()
        if not kw:
            continue
        lo = kw.lower()
        if lo in seen:
            continue
        seen.add(lo)
        out.append(kw)
    return out


def _tokens(keyword: str) -> list[str]:
    """Significant lowercase tokens from a keyword.

    Drops stop-words and tokens shorter than `_MIN_TOKEN_LEN`. Splits on
    any non-alphanumeric run.
    """
    return [
        t.lower()
        for t in _TOKEN_RE.findall(keyword)
        if len(t) >= _MIN_TOKEN_LEN and t.lower() not in _STOPWORDS
    ]


def match_project(haystack: str) -> KeywordMatch | None:
    """Return the best project match for the combined haystack, or None.

    The haystack is the caller's choice — typically window title + URL +
    browser tab title + OCR text concatenated. Empty / whitespace inputs
    return None.
    """
    if not haystack or not haystack.strip():
        return None
    norm_hay = _normalize(haystack)
    if len(norm_hay) < _MIN_NORMALIZED_LEN:
        return None

    rows = (
        get_connection()
        .execute(
            "SELECT id, name, match_keywords FROM projects "
            "WHERE is_active = 1 AND match_keywords IS NOT NULL AND match_keywords != '' "
            "ORDER BY id"
        )
        .fetchall()
    )
    return _best_match(norm_hay, rows)


def _best_match(norm_hay: str, project_rows: list) -> KeywordMatch | None:
    """Score every keyword against the (already normalised) haystack."""
    best: KeywordMatch | None = None
    for row in project_rows:
        for kw in _split_keywords(row["match_keywords"]):
            score = _score_keyword(kw, norm_hay)
            if score == 0:
                continue
            if best is None or score > best.score:
                best = KeywordMatch(int(row["id"]), str(row["name"]), kw, score)
    return best


def reclassify_stored_activities(only_unclassified: bool = True) -> dict[str, int]:
    """Re-run the matcher across already-stored activities AND sessions.

    Used by the /api/projects/reclassify endpoint and by the projects
    API on keyword changes — so the user doesn't need to wait for new
    captures to see their existing timeline pick up the rules they just
    typed.

    When ``only_unclassified`` is True (default), only rows whose
    ``project_id`` is NULL get reconsidered. Pass False to overwrite
    every existing assignment — useful after a major rules cleanup.

    Returns a counter dict:
      {scanned, matched, unchanged, sessions_scanned, sessions_matched}.
    """
    conn = get_connection()
    projects = conn.execute(
        "SELECT id, name, match_keywords FROM projects "
        "WHERE is_active = 1 AND match_keywords IS NOT NULL AND match_keywords != '' "
        "ORDER BY id"
    ).fetchall()
    if not projects:
        return {
            "scanned": 0,
            "matched": 0,
            "unchanged": 0,
            "sessions_scanned": 0,
            "sessions_matched": 0,
        }

    # ── Activities pass ─────────────────────────────────────────────
    where = "WHERE project_id IS NULL" if only_unclassified else ""
    activity_rows = conn.execute(
        f"SELECT id, window_title, process_name, ocr_text, redacted_text, project_id "
        f"FROM activities {where}"
    ).fetchall()

    matched = 0
    unchanged = 0
    for row in activity_rows:
        parts = [row["window_title"], row["process_name"], row["ocr_text"], row["redacted_text"]]
        haystack = " ".join(p for p in parts if p)
        if not haystack.strip():
            unchanged += 1
            continue
        norm_hay = _normalize(haystack)
        if len(norm_hay) < _MIN_NORMALIZED_LEN:
            unchanged += 1
            continue
        hit = _best_match(norm_hay, projects)
        if hit is None or hit.project_id == row["project_id"]:
            unchanged += 1
            continue
        conn.execute(
            "UPDATE activities SET project_id = ?, source = 'keyword_match', "
            "confidence = 1.0 WHERE id = ?",
            (hit.project_id, row["id"]),
        )
        matched += 1

    # ── Sessions pass ───────────────────────────────────────────────
    # Sessions store the human-readable "process — title" string in
    # `description`. That's the same signal as the activity title, but
    # it's the column the timeline actually reads when deciding what
    # bucket to show the row in — so even if activities matched, the
    # session can still display "Unclassified" until we update it.
    #
    # We also pull OCR text from activities that overlap each session
    # so a session whose description is the useless "Edge and 8 more
    # pages" still classifies when its on-screen text proves the user
    # was on the Sceneryenzo Shopify admin (or any other project).
    session_rows = conn.execute(
        f"SELECT id, started_at, ended_at, description, project_id FROM sessions {where}"
    ).fetchall()

    sessions_matched = 0
    for row in session_rows:
        desc = row["description"] or ""
        ocr_blobs = conn.execute(
            "SELECT ocr_text FROM activities "
            "WHERE captured_at >= ? AND captured_at <= ? "
            "AND ocr_text IS NOT NULL AND ocr_text != '' "
            "LIMIT 20",
            (row["started_at"], row["ended_at"]),
        ).fetchall()
        ocr_combined = " ".join(o["ocr_text"] for o in ocr_blobs if o["ocr_text"])
        haystack = (desc + " " + ocr_combined).strip()
        if not haystack:
            continue
        norm_hay = _normalize(haystack)
        if len(norm_hay) < _MIN_NORMALIZED_LEN:
            continue
        hit = _best_match(norm_hay, projects)
        if hit is None or hit.project_id == row["project_id"]:
            continue
        conn.execute(
            "UPDATE sessions SET project_id = ? WHERE id = ?",
            (hit.project_id, row["id"]),
        )
        sessions_matched += 1

    conn.commit()
    logger.info(
        "Reclassified: activities scanned=%d matched=%d, sessions scanned=%d matched=%d "
        "(only_unclassified=%s)",
        len(activity_rows),
        matched,
        len(session_rows),
        sessions_matched,
        only_unclassified,
    )
    return {
        "scanned": len(activity_rows),
        "matched": matched,
        "unchanged": unchanged,
        "sessions_scanned": len(session_rows),
        "sessions_matched": sessions_matched,
    }


def _score_keyword(keyword: str, norm_hay: str) -> int:
    """Compute how strongly `keyword` matches `norm_hay`. 0 = no match."""
    norm_kw = _normalize(keyword)
    if len(norm_kw) >= _MIN_NORMALIZED_LEN and norm_kw in norm_hay:
        # Whole-keyword normalized substring — strongest signal.
        return len(norm_kw) * 2

    toks = _tokens(keyword)
    if not toks:
        return 0
    matched_chars = sum(len(t) for t in toks if t in norm_hay)
    return matched_chars
