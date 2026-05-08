"""OpenAI Chat Completions API client using httpx."""

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

_API_URL = "https://api.openai.com/v1/chat/completions"
_TIMEOUT_SECONDS = 10.0


class OpenAIClient(LLMClient):
    """OpenAI implementation of the classifier protocol."""

    provider = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
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
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        started = time.monotonic()
        try:
            payload = _post(self._client, _API_URL, headers, body)
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        text = _extract_text(payload)
        usage = payload.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
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
    if client is not None:
        response = client.post(url, headers=headers, json=body, timeout=_TIMEOUT_SECONDS)
    else:
        with httpx.Client(timeout=_TIMEOUT_SECONDS) as transient:
            response = transient.post(url, headers=headers, json=body)
    response.raise_for_status()
    out: dict[str, Any] = response.json()
    return out


def _extract_text(payload: dict[str, Any]) -> str:
    """Pull the first message content from a Chat Completions response."""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message") or {}
    return str(message.get("content") or "")
