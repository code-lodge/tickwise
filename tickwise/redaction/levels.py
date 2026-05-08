"""Privacy-level metadata: which categories apply at each level.

The actual pattern dictionaries live in :mod:`patterns`; this module
exists so the dashboard can render a "what gets redacted at level N"
explanation without re-discovering the structure.
"""

from __future__ import annotations

from typing import Final

from tickwise.redaction.patterns import (
    L1_PATTERNS,
    L2_PATTERNS,
    L3_PATTERNS,
    L4_PATTERNS,
)

LEVEL_DESCRIPTIONS: Final[dict[int, str]] = {
    1: "Minimal — strip API keys, passwords, private keys, JWTs, connection strings.",
    2: "Standard — Level 1 plus emails, phones, IPs, IBANs, file paths, addresses.",
    3: "Aggressive — Level 1+2 plus names, organisations, amounts, chat content.",
    4: "Maximum — Level 1+2+3 plus URLs, code blocks, prose, proper nouns.",
}


def categories_for_level(level: int) -> list[str]:
    """Return the ordered category labels active at the given level."""
    if level < 1 or level > 4:
        raise ValueError(f"privacy level must be 1-4, got {level}")
    out: list[str] = list(L1_PATTERNS.keys())
    if level >= 2:
        out.extend(k for k in L2_PATTERNS if k not in out)
    if level >= 3:
        out.extend(k for k in L3_PATTERNS if k not in out)
    if level >= 4:
        out.extend(k for k in L4_PATTERNS if k not in out)
    return out
