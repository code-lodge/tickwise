"""Pattern-level unit tests for the redaction engine."""

from __future__ import annotations

import pytest

from tickwise.redaction.engine import RedactionEngine, redact_for_level
from tickwise.redaction.levels import LEVEL_DESCRIPTIONS, categories_for_level
from tickwise.redaction.patterns import (
    L1_PATTERNS,
    L2_PATTERNS,
    is_loopback_ip,
    patterns_for_level,
)


@pytest.mark.unit
class TestLevel1Patterns:
    def test_api_key_openai(self) -> None:
        result = redact_for_level("token: sk-proj-AAAAaaaa12345678901234567890abcd", level=1)
        assert "[API_KEY]" in result
        assert "sk-proj-" not in result

    def test_api_key_github(self) -> None:
        result = redact_for_level("export GH=ghp_aaaaaaaaaaaaaaaaaaaaaaaa", level=1)
        assert "[API_KEY]" in result

    def test_password_keyword(self) -> None:
        result = redact_for_level("password: hunter2", level=1)
        assert "[PASSWORD]" in result
        assert "hunter2" not in result

    def test_password_dutch(self) -> None:
        result = redact_for_level("wachtwoord = geheim", level=1)
        assert "[PASSWORD]" in result

    def test_jwt(self) -> None:
        jwt = "eyJabcdefghij.eyJklmnopqrst.signature"
        result = redact_for_level(f"auth: {jwt}", level=1)
        assert "[JWT]" in result

    def test_private_key_block(self) -> None:
        block = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQ\n-----END RSA PRIVATE KEY-----"
        result = redact_for_level(block, level=1)
        assert "[PRIVATE_KEY]" in result
        assert "MIIEowIBAAKCAQ" not in result

    def test_connection_string(self) -> None:
        result = redact_for_level("postgres://user:pass@host:5432/db", level=1)
        assert "[CONNECTION_STRING]" in result

    def test_env_var_lines(self) -> None:
        sample = "DB_PASSWORD=secret\nAWS_SECRET=abc123"
        result = redact_for_level(sample, level=1)
        assert "[ENV_VAR]" in result

    def test_level_1_does_not_redact_email(self) -> None:
        result = redact_for_level("Contact: alice@example.com", level=1)
        assert "alice@example.com" in result


@pytest.mark.unit
class TestLevel2Patterns:
    def test_email(self) -> None:
        result = redact_for_level("alice@example.com", level=2)
        assert "[EMAIL]" in result
        assert "alice" not in result or "@example.com" not in result

    def test_ipv4_redacted(self) -> None:
        result = redact_for_level("Server is at 10.0.1.4", level=2)
        assert "[IP_ADDRESS]" in result

    def test_loopback_kept(self) -> None:
        result = redact_for_level("Service on 127.0.0.1", level=2)
        assert "127.0.0.1" in result

    def test_url_keeps_domain(self) -> None:
        result = redact_for_level("Visit https://example.com/path?x=1", level=2)
        assert "[URL:example.com]" in result
        assert "/path?x=1" not in result

    def test_path_windows(self) -> None:
        result = redact_for_level(r"open C:\Users\alice\notes.txt", level=2)
        assert "[PATH]" in result

    def test_path_unix(self) -> None:
        result = redact_for_level("/home/alice/notes.txt", level=2)
        assert "[PATH]" in result

    def test_iban(self) -> None:
        result = redact_for_level("IBAN NL91ABNA0417164300 here", level=2)
        assert "[IBAN]" in result

    def test_mac_address(self) -> None:
        result = redact_for_level("MAC 01:23:45:67:89:AB", level=2)
        assert "[MAC_ADDRESS]" in result


@pytest.mark.unit
class TestLevel4Patterns:
    def test_url_fully_removed(self) -> None:
        result = redact_for_level("Go to https://example.com/path", level=4)
        assert "[URL]" in result
        assert "example.com" not in result

    def test_long_number(self) -> None:
        result = redact_for_level("Order 1234567890", level=4)
        assert "[NUMBER]" in result


@pytest.mark.unit
class TestEngine:
    def test_invalid_level_rejected(self) -> None:
        with pytest.raises(ValueError):
            RedactionEngine(privacy_level=0)
        with pytest.raises(ValueError):
            RedactionEngine(privacy_level=5)

    def test_empty_text_returns_empty(self) -> None:
        result = RedactionEngine().redact("")
        assert result.redacted_text == ""
        assert result.redaction_count == 0

    def test_categories_hit_recorded(self) -> None:
        engine = RedactionEngine(privacy_level=2)
        result = engine.redact("Email alice@example.com and key sk-test12345678901234567890abc")
        assert "EMAIL" in result.categories_hit
        assert "API_KEY" in result.categories_hit
        assert result.redaction_count >= 2

    def test_max_chars_truncation(self) -> None:
        engine = RedactionEngine(privacy_level=1, max_chars=20)
        result = engine.redact("hello world " * 50)
        assert len(result.redacted_text) <= 21  # +1 for the ellipsis

    def test_long_input_does_not_crash(self) -> None:
        engine = RedactionEngine(privacy_level=4, max_chars=2000)
        big = "lorem ipsum dolor sit amet " * 500
        result = engine.redact(big)
        assert isinstance(result.redacted_text, str)


@pytest.mark.unit
class TestLevels:
    def test_descriptions_for_all_levels(self) -> None:
        assert {1, 2, 3, 4} <= LEVEL_DESCRIPTIONS.keys()

    def test_categories_for_level_extends(self) -> None:
        l1 = set(categories_for_level(1))
        l2 = set(categories_for_level(2))
        l3 = set(categories_for_level(3))
        l4 = set(categories_for_level(4))
        assert l1 < l2 <= l3 <= l4

    def test_invalid_level_rejected(self) -> None:
        with pytest.raises(ValueError):
            categories_for_level(0)
        with pytest.raises(ValueError):
            patterns_for_level(99)


@pytest.mark.unit
class TestHelpers:
    def test_is_loopback(self) -> None:
        assert is_loopback_ip("127.0.0.1") is True
        assert is_loopback_ip("0.0.0.0") is True
        assert is_loopback_ip("::1") is True
        assert is_loopback_ip("8.8.8.8") is False

    def test_l1_patterns_present(self) -> None:
        assert "API_KEY" in L1_PATTERNS
        assert "PRIVATE_KEY" in L1_PATTERNS

    def test_l2_patterns_present(self) -> None:
        assert "EMAIL" in L2_PATTERNS
        assert "IP_ADDRESS" in L2_PATTERNS
