"""Pydantic models corresponding to database tables."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Project(BaseModel):
    id: int | None = None
    name: str
    color: str = "#3B82F6"
    client_id: int | None = None
    hourly_rate: float | None = None
    currency: str = "USD"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Client(BaseModel):
    id: int | None = None
    name: str
    email: str | None = None
    timezone: str = "UTC"
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaskCategory(BaseModel):
    id: int | None = None
    name: str
    color: str = "#6B7280"
    project_id: int | None = None
    created_at: datetime | None = None


class Activity(BaseModel):
    id: int | None = None
    captured_at: datetime
    window_title: str | None = None
    process_name: str | None = None
    app_name: str | None = None
    url: str | None = None
    ocr_text: str | None = None
    redacted_text: str | None = None
    phash: str | None = None
    privacy_level: int = 2
    change_detected: bool = False
    source: str = "pending_classification"
    created_at: datetime | None = None


class Session(BaseModel):
    id: int | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_secs: int | None = None
    project_id: int | None = None
    category_id: int | None = None
    description: str | None = None
    tags: str | None = None
    is_manual: bool = False
    is_billed: bool = False
    invoice_id: int | None = None
    llm_classified: bool = False
    confidence: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PomodoroSession(BaseModel):
    id: int | None = None
    session_id: int | None = None
    type: Literal["work", "short_break", "long_break"]
    started_at: datetime
    ended_at: datetime | None = None
    completed: bool = False
    created_at: datetime | None = None


class Invoice(BaseModel):
    id: int | None = None
    client_id: int | None = None
    invoice_number: str
    issued_date: str
    due_date: str | None = None
    status: Literal["draft", "sent", "paid", "overdue", "cancelled"] = "draft"
    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    notes: str | None = None
    pdf_path: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InvoiceLineItem(BaseModel):
    id: int | None = None
    invoice_id: int
    session_id: int | None = None
    description: str
    hours: float = 0.0
    rate: float = 0.0
    amount: float = 0.0
    created_at: datetime | None = None


class FreelancerProfile(BaseModel):
    id: int = 1
    name: str = ""
    email: str = ""
    company: str | None = None
    address: str | None = None
    tax_id: str | None = None
    default_currency: str = "USD"
    default_hourly_rate: float | None = None
    timezone: str = "UTC"
    invoice_prefix: str = "INV"
    invoice_next_number: int = 1
    updated_at: datetime | None = None


class CalendarProvider(BaseModel):
    id: int | None = None
    name: str
    type: Literal["caldav", "google", "ical"]
    url: str | None = None
    username: str | None = None
    is_active: bool = True
    last_synced_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LLMConfig(BaseModel):
    id: int = 1
    provider: Literal["anthropic", "openai"] = "anthropic"
    model: str = "claude-haiku-4-5-20251001"
    api_key_ref: str | None = None
    temperature: float = 0.1
    max_tokens: int = 256
    updated_at: datetime | None = None


class ClassificationCache(BaseModel):
    id: int | None = None
    cache_key: str
    project_id: int | None = None
    category_id: int | None = None
    description: str | None = None
    confidence: float | None = None
    created_at: datetime | None = None
    expires_at: datetime


class CustomRedactionRule(BaseModel):
    id: int | None = None
    pattern: str
    replacement: str = "[REDACTED]"
    is_regex: bool = False
    is_active: bool = True
    created_at: datetime | None = None


class Setting(BaseModel):
    key: str
    value: str
    updated_at: datetime | None = None


class SettingsMap(BaseModel):
    """Flat dict of all settings (key → value)."""

    settings: dict[str, str] = Field(default_factory=dict)
