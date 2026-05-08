"""Unit tests for custom redaction rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from chronolens.db.connection import transaction
from chronolens.redaction.custom_rules import CustomRule, apply_rules, load_active_rules


def _insert_rule(pattern: str, mode: str = "contains", replacement: str = "[CLIENT]") -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO custom_redaction_rules
                (pattern, match_mode, replacement, is_active, is_regex)
            VALUES (?, ?, ?, 1, ?)
            """,
            (pattern, mode, replacement, 1 if mode == "regex" else 0),
        )


@pytest.mark.unit
class TestApplyRules:
    def test_contains_mode(self) -> None:
        rule = CustomRule(pattern="Klant XYZ", match_mode="contains", replacement="[CLIENT]")
        out, hits = apply_rules("Working with Klant XYZ today", [rule])
        assert "Klant XYZ" not in out
        assert "[CLIENT]" in out
        assert hits == 1

    def test_regex_mode(self) -> None:
        rule = CustomRule(pattern=r"192\.168\.1\.\d+", match_mode="regex", replacement="[HOME]")
        out, hits = apply_rules("Connect to 192.168.1.42 and 192.168.1.99", [rule])
        assert "[HOME]" in out
        assert hits == 2

    def test_exact_mode(self) -> None:
        rule = CustomRule(pattern="acme", match_mode="exact", replacement="[ORG]")
        out, _ = apply_rules("acme corp uses acmeware too", [rule])
        assert out.startswith("[ORG] corp")
        assert "acmeware" in out  # not redacted — partial match doesn't count

    def test_invalid_regex_skipped(self) -> None:
        rule = CustomRule(pattern="(unclosed", match_mode="regex", replacement="[X]")
        out, hits = apply_rules("text (unclosed", [rule])
        assert hits == 0
        assert out == "text (unclosed"

    def test_empty_inputs(self) -> None:
        assert apply_rules("", [CustomRule("x", "contains", "[X]")]) == ("", 0)
        assert apply_rules("text", []) == ("text", 0)


@pytest.mark.unit
class TestLoadActiveRules:
    def test_loads_only_active(self, tmp_db: Path) -> None:
        _insert_rule("alpha")
        with transaction() as conn:
            conn.execute(
                "INSERT INTO custom_redaction_rules (pattern, is_active) VALUES (?, 0)",
                ("inactive",),
            )
        rules = load_active_rules()
        assert [r.pattern for r in rules] == ["alpha"]
