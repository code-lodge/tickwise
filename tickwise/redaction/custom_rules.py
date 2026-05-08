"""Custom redaction rule loading and application.

User-defined rules from the `custom_redaction_rules` table are applied
*before* the level-based patterns and regardless of the level. Three
match modes are supported:

- ``contains`` — case-sensitive substring match (the simplest UX).
- ``exact``   — full-token match, anchored on word boundaries.
- ``regex``   — arbitrary Python regex; invalid patterns are skipped.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from tickwise.db.connection import get_connection

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CustomRule:
    """An active custom redaction rule loaded from the database."""

    pattern: str
    match_mode: str
    replacement: str


def load_active_rules() -> list[CustomRule]:
    """Return every active custom rule, in id order. Empty list on error."""
    try:
        rows = (
            get_connection()
            .execute(
                "SELECT pattern, match_mode, replacement FROM custom_redaction_rules " "WHERE is_active = 1 ORDER BY id"
            )
            .fetchall()
        )
    except Exception:
        logger.exception("loading custom redaction rules failed")
        return []
    return [
        CustomRule(
            pattern=row["pattern"],
            match_mode=row["match_mode"] or "contains",
            replacement=row["replacement"] or "[REDACTED]",
        )
        for row in rows
    ]


def apply_rules(text: str, rules: list[CustomRule]) -> tuple[str, int]:
    """Apply each rule to `text`. Returns (redacted, total_match_count)."""
    if not text or not rules:
        return text, 0
    total = 0
    for rule in rules:
        text, hits = _apply_one(text, rule)
        total += hits
    return text, total


def _apply_one(text: str, rule: CustomRule) -> tuple[str, int]:
    if rule.match_mode == "regex":
        try:
            compiled = re.compile(rule.pattern)
        except re.error:
            logger.warning("ignoring invalid custom regex %r", rule.pattern)
            return text, 0
        return compiled.subn(rule.replacement, text)
    if rule.match_mode == "exact":
        compiled = re.compile(rf"\b{re.escape(rule.pattern)}\b")
        return compiled.subn(rule.replacement, text)
    # default: contains (case-sensitive substring)
    if not rule.pattern:
        return text, 0
    count = text.count(rule.pattern)
    if count == 0:
        return text, 0
    return text.replace(rule.pattern, rule.replacement), count
