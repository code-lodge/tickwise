"""The orchestrating RedactionEngine.

Application order (per spec §4):

1. Custom rules (user-defined; always applied).
2. Level-based patterns: L1 secrets → L2 PII → L3 content → L4 broad.
3. Final pass: collapse repeated whitespace, trim to `max_chars`.

The engine also tracks which categories triggered for the redaction log,
so the dashboard can report transparency stats without storing the raw
content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import cast

from tickwise.config import DEFAULTS
from tickwise.redaction.custom_rules import CustomRule, apply_rules
from tickwise.redaction.patterns import (
    is_loopback_ip,
    patterns_for_level,
)


@dataclass(frozen=True, slots=True)
class RedactionResult:
    """Outcome of one redaction pass — what was redacted and what fired."""

    redacted_text: str
    original_length: int
    redacted_length: int
    redaction_count: int
    categories_hit: list[str] = field(default_factory=list)


class RedactionEngine:
    """Stateful, reusable engine. Recreate when level or custom rules change."""

    def __init__(
        self,
        privacy_level: int = 2,
        custom_rules: list[CustomRule] | None = None,
        max_chars: int | None = None,
    ) -> None:
        if privacy_level < 1 or privacy_level > 4:
            raise ValueError(f"privacy_level must be 1-4, got {privacy_level}")
        self.privacy_level = privacy_level
        self.custom_rules = custom_rules or []
        self.max_chars = max_chars if max_chars is not None else int(cast(int, DEFAULTS["redaction_max_chars"]))
        self._patterns = patterns_for_level(privacy_level)

    # ─── public API ────────────────────────────────────────────────────

    def redact(self, text: str | None) -> RedactionResult:
        """Redact a single string. None and empty input return empty result."""
        if not text:
            return RedactionResult(
                redacted_text="",
                original_length=0,
                redacted_length=0,
                redaction_count=0,
            )
        original_length = len(text)
        out = text
        total_hits = 0
        hit_categories: list[str] = []

        out, custom_hits = apply_rules(out, self.custom_rules)
        if custom_hits:
            total_hits += custom_hits
            hit_categories.append("CUSTOM")

        for category, pattern in self._patterns.items():
            if category == "IP_ADDRESS" and self.privacy_level >= 2:
                # Special case — keep loopback addresses readable.
                out, hits = self._sub_ipaddress(pattern, out)
            elif category == "URL" and self.privacy_level == 2:
                # Level 2 URL handling: keep scheme + host, strip path/query.
                out, hits = self._sub_url_keep_domain(pattern, out)
            else:
                out, hits = pattern.subn(f"[{category}]", out)
            if hits:
                total_hits += hits
                if category not in hit_categories:
                    hit_categories.append(category)

        out = self._final_pass(out)
        return RedactionResult(
            redacted_text=out,
            original_length=original_length,
            redacted_length=len(out),
            redaction_count=total_hits,
            categories_hit=hit_categories,
        )

    # ─── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _sub_ipaddress(pattern: re.Pattern[str], text: str) -> tuple[str, int]:
        hits = 0

        def repl(match: re.Match[str]) -> str:
            nonlocal hits
            ip = match.group(0)
            if is_loopback_ip(ip):
                return ip
            hits += 1
            return "[IP_ADDRESS]"

        return pattern.sub(repl, text), hits

    @staticmethod
    def _sub_url_keep_domain(pattern: re.Pattern[str], text: str) -> tuple[str, int]:
        hits = 0

        def repl(match: re.Match[str]) -> str:
            nonlocal hits
            domain = match.group(1)
            scheme = "https" if match.group(0).lower().startswith("https") else "http"
            hits += 1
            return f"{scheme}://[URL:{domain}]"

        return pattern.sub(repl, text), hits

    def _final_pass(self, text: str) -> str:
        """Collapse whitespace and trim to `max_chars`."""
        compact = re.sub(r"[ \t]+", " ", text)
        compact = re.sub(r"\n{3,}", "\n\n", compact).strip()
        if self.max_chars and len(compact) > self.max_chars:
            compact = compact[: self.max_chars].rstrip() + "…"
        return compact


def redact_for_level(text: str, level: int = 2, max_chars: int | None = None) -> str:
    """Convenience helper for tests and one-off use; no custom rules."""
    return RedactionEngine(privacy_level=level, max_chars=max_chars).redact(text).redacted_text
