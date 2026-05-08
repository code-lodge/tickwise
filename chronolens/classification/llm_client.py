"""Common types and base class for LLM classification clients."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Parsed classifier output plus billing metadata."""

    project: str | None
    task: str | None
    confidence: float
    reasoning: str
    raw_json: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    success: bool = True
    error: str | None = None


class LLMError(Exception):
    """Raised when the upstream API call fails irrecoverably."""


class LLMClient(ABC):
    """Abstract classifier — concrete subclasses talk to specific providers."""

    provider: str = "abstract"

    def __init__(self, api_key: str, model: str, *, max_tokens: int = 256, temperature: float = 0.0) -> None:
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    @abstractmethod
    def classify(self, system_prompt: str, user_prompt: str) -> ClassificationResult:
        """Call the LLM and return a parsed `ClassificationResult`.

        Implementations must raise `LLMError` on transport failures so the
        pipeline can fall back to `pending_classification`.
        """


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse_classification_json(text: str) -> dict[str, Any]:
    """Coerce the model's text response into a JSON object.

    Models occasionally wrap JSON in code fences or add a brief preamble;
    this helper finds the first ``{...}`` block and parses it. Returns an
    empty dict if no JSON is found, and raises `ValueError` if the
    extracted block is malformed.
    """
    if not text:
        return {}
    match = _JSON_OBJECT.search(text)
    if not match:
        return {}
    parsed: dict[str, Any] = json.loads(match.group(0))
    return parsed


def build_result(
    raw_text: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
) -> ClassificationResult:
    """Translate raw LLM text + token counts into a `ClassificationResult`."""
    try:
        parsed = parse_classification_json(raw_text)
    except ValueError as exc:
        logger.warning("LLM returned malformed JSON: %s", exc)
        return ClassificationResult(
            project=None,
            task=None,
            confidence=0.0,
            reasoning="",
            raw_json=raw_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=False,
            error="invalid_json",
        )
    project = parsed.get("project") if isinstance(parsed.get("project"), str) else None
    task = parsed.get("task") if isinstance(parsed.get("task"), str) else None
    confidence_raw = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    reasoning = parsed.get("reasoning") or ""
    return ClassificationResult(
        project=project,
        task=task,
        confidence=confidence,
        reasoning=str(reasoning),
        raw_json=raw_text,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        success=True,
    )
