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

    best: KeywordMatch | None = None
    for row in rows:
        for kw in _split_keywords(row["match_keywords"]):
            score = _score_keyword(kw, norm_hay)
            if score == 0:
                continue
            if best is None or score > best.score:
                best = KeywordMatch(int(row["id"]), str(row["name"]), kw, score)
    return best


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
