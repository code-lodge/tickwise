"""Unit tests for chronolens.db.models — Pydantic schema validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from chronolens.db.models import (
    Activity,
    CalendarProvider,
    ClassificationCache,
    Client,
    CustomRedactionRule,
    FreelancerProfile,
    Invoice,
    InvoiceLineItem,
    LLMConfig,
    PomodoroSession,
    Project,
    Session,
    Setting,
    SettingsMap,
    TaskCategory,
)


@pytest.mark.unit
class TestProjectModel:
    def test_defaults(self) -> None:
        p = Project(name="My Project")
        assert p.color == "#3B82F6"
        assert p.currency == "USD"
        assert p.is_active is True
        assert p.id is None

    def test_full_construction(self) -> None:
        p = Project(name="Dev", color="#FF0000", hourly_rate=120.0, currency="EUR")
        assert p.hourly_rate == 120.0
        assert p.currency == "EUR"


@pytest.mark.unit
class TestClientModel:
    def test_defaults(self) -> None:
        c = Client(name="Acme")
        assert c.timezone == "UTC"
        assert c.email is None

    def test_email_optional(self) -> None:
        c = Client(name="Acme", email="ceo@acme.com")
        assert c.email == "ceo@acme.com"


@pytest.mark.unit
class TestTaskCategoryModel:
    def test_defaults(self) -> None:
        tc = TaskCategory(name="Development")
        assert tc.color == "#6B7280"
        assert tc.project_id is None


@pytest.mark.unit
class TestActivityModel:
    def test_required_field(self) -> None:
        now = datetime.now(UTC)
        a = Activity(captured_at=now)
        assert a.captured_at == now
        assert a.privacy_level == 2
        assert a.change_detected is False


@pytest.mark.unit
class TestSessionModel:
    def test_defaults(self) -> None:
        now = datetime.now(UTC)
        s = Session(started_at=now)
        assert s.is_manual is False
        assert s.is_billed is False
        assert s.llm_classified is False
        assert s.confidence is None


@pytest.mark.unit
class TestPomodoroSessionModel:
    def test_work_type(self) -> None:
        now = datetime.now(UTC)
        p = PomodoroSession(type="work", started_at=now)
        assert p.completed is False

    def test_break_types(self) -> None:
        now = datetime.now(UTC)
        assert PomodoroSession(type="short_break", started_at=now).type == "short_break"
        assert PomodoroSession(type="long_break", started_at=now).type == "long_break"


@pytest.mark.unit
class TestInvoiceModel:
    def test_defaults(self) -> None:
        inv = Invoice(invoice_number="INV-001", issued_date="2024-01-01")
        assert inv.status == "draft"
        assert inv.currency == "USD"
        assert inv.total == 0.0

    def test_statuses(self) -> None:
        for status in ("draft", "sent", "paid", "overdue", "cancelled"):
            inv = Invoice(invoice_number="X", issued_date="2024-01-01", status=status)  # type: ignore[arg-type]
            assert inv.status == status


@pytest.mark.unit
class TestInvoiceLineItemModel:
    def test_required_fields(self) -> None:
        item = InvoiceLineItem(invoice_id=1, description="Dev work")
        assert item.hours == 0.0
        assert item.rate == 0.0
        assert item.amount == 0.0


@pytest.mark.unit
class TestFreelancerProfileModel:
    def test_singleton_id(self) -> None:
        fp = FreelancerProfile()
        assert fp.id == 1

    def test_defaults(self) -> None:
        fp = FreelancerProfile()
        assert fp.default_currency == "USD"
        assert fp.timezone == "UTC"
        assert fp.invoice_prefix == "INV"


@pytest.mark.unit
class TestCalendarProviderModel:
    def test_caldav_type(self) -> None:
        cp = CalendarProvider(name="My CalDAV", type="caldav", url="https://cal.example.com")
        assert cp.is_active is True
        assert cp.last_synced_at is None


@pytest.mark.unit
class TestLLMConfigModel:
    def test_defaults(self) -> None:
        cfg = LLMConfig()
        assert cfg.provider == "anthropic"
        assert cfg.temperature == 0.1
        assert cfg.max_tokens == 256


@pytest.mark.unit
class TestClassificationCacheModel:
    def test_required_fields(self) -> None:
        expires = datetime.now(UTC)
        cache = ClassificationCache(cache_key="abc123", expires_at=expires)
        assert cache.confidence is None


@pytest.mark.unit
class TestCustomRedactionRuleModel:
    def test_defaults(self) -> None:
        rule = CustomRedactionRule(pattern=r"\d{4}-\d{4}-\d{4}-\d{4}")
        assert rule.replacement == "[REDACTED]"
        assert rule.is_regex is False
        assert rule.is_active is True


@pytest.mark.unit
class TestSettingModel:
    def test_construction(self) -> None:
        s = Setting(key="privacy_level", value="2")
        assert s.key == "privacy_level"
        assert s.value == "2"


@pytest.mark.unit
class TestSettingsMapModel:
    def test_empty_default(self) -> None:
        sm = SettingsMap()
        assert sm.settings == {}

    def test_with_data(self) -> None:
        sm = SettingsMap(settings={"privacy_level": "2", "ocr_enabled": "true"})
        assert sm.settings["privacy_level"] == "2"
