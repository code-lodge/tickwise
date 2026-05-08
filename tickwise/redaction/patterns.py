"""All regex patterns for the redaction engine, grouped by category.

Each entry maps a category label (used as the placeholder, e.g. ``EMAIL``
becomes ``[EMAIL]``) to a precompiled regex. The dict order matters when
patterns might overlap — earlier patterns redact first, so the one with
the most context wins (e.g. PRIVATE_KEY before BASE64_BLOB).

Phase 3 covers the full §4 set across all four privacy levels.
"""

from __future__ import annotations

import re
from typing import Final

# Reuse the same compiled regex everywhere — these are hot in the loop.

# ─── Level 1 — high-risk secrets ─────────────────────────────────────────

L1_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    # Multi-line blocks first so their inner contents aren't re-redacted
    # by lower-precedence patterns.
    "PRIVATE_KEY": re.compile(r"-----BEGIN[\s\w]*PRIVATE KEY-----[\s\S]*?-----END[\s\w]*PRIVATE KEY-----"),
    "PGP_BLOCK": re.compile(r"-----BEGIN PGP[\s\S]*?-----END PGP[\w\s-]*-----"),
    "CERTIFICATE": re.compile(r"-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----"),
    "SSH_KEY": re.compile(r"\bssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/=]{20,}"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\b"),
    "API_KEY": re.compile(
        r"(?:"
        r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"
        r"|ghp_[A-Za-z0-9]{20,}"
        r"|gho_[A-Za-z0-9]{20,}"
        r"|glpat-[A-Za-z0-9_-]{10,}"
        r"|AKIA[0-9A-Z]{16}"
        r"|xox[bpsa]-[A-Za-z0-9-]{10,}"
        r"|Bearer\s+[A-Za-z0-9._-]{20,}"
        r"|token[\s:=]+[A-Za-z0-9._-]{20,}"
        r")"
    ),
    "CLOUD_CREDENTIAL": re.compile(
        r"(?:"
        r"AKIA[0-9A-Z]{16}"
        r"|DefaultEndpointsProtocol=https?;[A-Za-z0-9=;+/_.-]+"
        r"|\"type\":\s*\"service_account\""
        r")"
    ),
    "PASSWORD": re.compile(
        r"\b(?:password|passwd|secret|wachtwoord)[\s:=]+\S+",
        re.IGNORECASE,
    ),
    "CONNECTION_STRING": re.compile(r"\b(?:mysql|postgres|postgresql|mongodb|mongodb\+srv|redis|amqp|mssql)://\S+"),
    "ENV_VAR": re.compile(r"(?m)^[A-Z][A-Z0-9_]+=\S.*$"),
    "BASE64_BLOB": re.compile(r"[A-Za-z0-9+/=]{100,}"),
    "HEX_SECRET": re.compile(r"(?i)(?:key|token|secret|hash)[\s:=\"]*([0-9a-fA-F]{32,})"),
}


# ─── Level 2 — PII, network, financial identifiers ─────────────────────────

# IPv4 only, but we filter loopbacks during application — the regex itself
# matches any dotted quad; the engine drops `127.0.0.1`, `0.0.0.0`,
# `localhost` after the match.
L2_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "EMAIL": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}"),
    # MAC must come before IP_ADDRESS — the IPv6 fragment of IP_ADDRESS
    # would otherwise swallow `01:23:45:67:89:AB` as a partial v6.
    "MAC_ADDRESS": re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"),
    "IP_ADDRESS": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b" r"|\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b"),
    # Phone numbers — anchor with a digit-grouping prefix so we don't
    # eat plain integers like "1234567890" that NUMBER (L4) should catch.
    "PHONE": re.compile(r"(?:\+\d{1,3}[\s.-]\d|\b\d{2,4}[\s.-]\d{2,4}[\s.-]\d{2,4})" r"(?:[\s.-]?\d{1,4})*"),
    "URL": re.compile(r"https?://([^/\s]+)\S*"),
    "PATH": re.compile(r"(?:[A-Z]:\\[\w\s\\.-]+|/(?:home|Users|etc|var|opt|usr/local)/[\w./~ -]+)"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b"),
    "NATIONAL_ID": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b|(?:bsn|burgerservicenummer)[\s:#]*\d{8,9}\b",
        re.IGNORECASE,
    ),
    "ADDRESS": re.compile(r"\b\d{4}\s?[A-Z]{2}\b|\b\d{5}(?:-\d{4})?\b"),
    "DOB": re.compile(
        r"(?:dob|date\s+of\s+birth|geboren|birth|geboortedatum)[\s:]*\d{1,4}[\-/.]\d{1,2}[\-/.]\d{1,4}",
        re.IGNORECASE,
    ),
}


# ─── Level 3 — content / business signal ────────────────────────────────

L3_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "PERSON": re.compile(
        r"(?:(?<=^)|(?<=\s))(?:Dear|From:|To:|Hi|Hello|Beste|Geachte|@)\s+"
        r"([A-Z][a-zà-öø-ÿ]+(?:\s[A-Z][a-zà-öø-ÿ]+){0,2})"
    ),
    "ORG": re.compile(
        r"\b[A-Z][\w&]+(?:\s+[A-Z][\w&]+){0,3}\s+(?:BV|B\.V\.|NV|N\.V\.|VOF|LLC|Inc\.?|GmbH|Ltd\.?|Corp\.?)\b"
    ),
    "AMOUNT": re.compile(r"(?:[€$£¥]\s?\d[\d.,]*" r"|\b\d[\d.,]*\s?(?:EUR|USD|GBP|JPY)\b)"),
    "ID_NUMBER": re.compile(r"\b(?:INV[-#]?\d+|ORD[-#]?\d+|KVK[-:#\s]?\d+|#\d{3,})\b"),
    "CHAT_MESSAGE": re.compile(r"(?m)^\s*\d{1,2}:\d{2}(?::\d{2})?\s+\S+\s+.+$"),
    "COMMAND": re.compile(
        r"(?m)^[\s>$#]+(?:curl|wget|ssh|scp|docker|kubectl|git|npm|pip|cargo)\b.*$" r"|^[\s>$#]\s+\S.*$"
    ),
    "CODE_DIFF": re.compile(r"(?m)^(?:diff --git\s.*|index\s.*|@@.*@@.*|[+-]{1,3}\s.*)$"),
    "HTTP_HEADER": re.compile(r"(?im)^(?:Cookie|Authorization|Set-Cookie|X-[A-Za-z-]+):\s+.+$"),
    "LOG_CONTENT": re.compile(
        r"(?m)^\s*\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}.*" r"(?:DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE).*$"
    ),
}


# ─── Level 4 — broad content reduction ──────────────────────────────────

L4_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    # Code blocks (heuristic — sequences of code-like lines).
    "CODE_BLOCK": re.compile(
        r"(?m)(?:^.*(?:[{}]|=>|->|\bfunction\b|\bclass\b|\bimport\b|\bconst\b|\blet\b|\bvar\b|\bdef\b|if\s*\(|for\s*\().*$\n?){3,}"
    ),
    "TEXT_BLOCK": re.compile(r"(?:[A-Z][^.!?\n]{20,}[.!?]\s+){3,}"),
    # Catch any URL completely (Level 4 strips even domains).
    "URL": re.compile(r"https?://\S+"),
    "QUOTED": re.compile(r"\"[^\"\n]{4,}\"|«[^»]{4,}»|'[^'\n]{8,}'"),
    "TABLE_DATA": re.compile(r"(?m)(?:^\s*\|[^\n]*\|.*$\n?){2,}|(?:^[^,\n]+,[^,\n]+,[^,\n]+.*$\n?){2,}"),
    "PROPER_NOUN": re.compile(r"\b[A-Z][a-zà-öø-ÿ]+(?:\s+[A-Z][a-zà-öø-ÿ]+){1,}\b"),
    "DOMAIN": re.compile(r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "NUMBER": re.compile(r"\b\d{5,}\b"),
    "NON_ASCII": re.compile(r"[^\x00-\x7F]+"),
}


def patterns_for_level(level: int) -> dict[str, re.Pattern[str]]:
    """Return the merged ordered pattern dict for the given level."""
    if level < 1 or level > 4:
        raise ValueError(f"privacy level must be 1-4, got {level}")
    out: dict[str, re.Pattern[str]] = {}
    out.update(L1_PATTERNS)
    if level >= 2:
        out.update(L2_PATTERNS)
    if level >= 3:
        out.update(L3_PATTERNS)
    if level >= 4:
        # Level 4's URL pattern intentionally overrides Level 2's (which
        # only stripped paths, keeping the domain).
        out.update(L4_PATTERNS)
    return out


_LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "0.0.0.0", "::1", "localhost"})


def is_loopback_ip(ip: str) -> bool:
    """True for the loopback addresses we keep unredacted at Level 2."""
    return ip in _LOOPBACK_HOSTS
