"""Anthropic Messages API client using httpx."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from chronolens.classification.llm_client import (
    ClassificationResult,
    LLMClient,
    LLMError,
    build_result,
)

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_TIMEOUT_SECONDS = 10.0


class ClaudeClient(LLMClient):
    """Anthropic implementation of the classifier protocol."""

    provider = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(api_key, model, max_tokens=max_tokens, temperature=temperature)
        self._client = client

    def classify(self, system_prompt: str, user_prompt: str) -> ClassificationResult:
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": _API_VERSION,
            "content-type": "application/json",
        }

        started = time.monotonic()
        try:
            payload = _post(self._client, _API_URL, headers, body)
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        text = _extract_text(payload)
        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("input_tokens", 0) or 0)
        completion_tokens = int(usage.get("output_tokens", 0) or 0)
        return build_result(
            text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )


def _post(
    client: httpx.Client | None,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
) -> dict[str, Any]:
    """Issue the POST request with a transient client when one isn't injected."""
    if client is not None:
        response = client.post(url, headers=headers, json=body, timeout=_TIMEOUT_SECONDS)
    else:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as transient:
            response = transient.post(url, headers=headers, json=body)
    response.raise_for_status()
    out: dict[str, Any] = response.json()
    return out


def _extract_text(payload: dict[str, Any]) -> str:
    """Pull the first text block from an Anthropic Messages response."""
    content = payload.get("content") or []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            return str(block.get("text") or "")
    return ""
