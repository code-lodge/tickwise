"""Unit tests for the LLM clients (no real network calls)."""

from __future__ import annotations

import httpx
import pytest

from chronolens.classification.claude_client import ClaudeClient
from chronolens.classification.llm_client import (
    LLMError,
    build_result,
    parse_classification_json,
)
from chronolens.classification.openai_client import OpenAIClient
from chronolens.classification.prompts import (
    SYSTEM_PROMPT,
    ClassificationContext,
    ProjectChoice,
    build_user_prompt,
)


def _mock_client(payload: dict, status: int = 200) -> httpx.Client:
    transport = httpx.MockTransport(lambda req: httpx.Response(status, json=payload))
    return httpx.Client(transport=transport)


@pytest.mark.unit
class TestParseJSON:
    def test_clean_json(self) -> None:
        out = parse_classification_json('{"project": "X", "confidence": 0.9}')
        assert out["project"] == "X"

    def test_with_preamble(self) -> None:
        text = 'Sure, here you go:\n```json\n{"project": "Y"}\n```'
        out = parse_classification_json(text)
        assert out["project"] == "Y"

    def test_empty(self) -> None:
        assert parse_classification_json("") == {}

    def test_no_json(self) -> None:
        assert parse_classification_json("just plain text") == {}

    def test_malformed_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_classification_json("{not real json}")


@pytest.mark.unit
class TestBuildResult:
    def test_clamps_confidence(self) -> None:
        r = build_result(
            '{"project": "p", "task": "t", "confidence": 1.5, "reasoning": "x"}',
            prompt_tokens=10,
            completion_tokens=5,
            latency_ms=20,
        )
        assert r.confidence == 1.0
        assert r.success is True
        assert r.task == "t"

    def test_invalid_json_marks_failure(self) -> None:
        # Has matching braces but invalid JSON inside — parser reaches the regex
        # match and json.loads then raises.
        r = build_result("hello {not valid json}", prompt_tokens=0, completion_tokens=0, latency_ms=0)
        assert r.success is False
        assert r.error == "invalid_json"

    def test_string_confidence_falls_back_to_zero(self) -> None:
        r = build_result(
            '{"project": null, "confidence": "low", "reasoning": ""}',
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
        )
        assert r.confidence == 0.0


@pytest.mark.unit
class TestClaudeClient:
    def test_classify_parses_response(self) -> None:
        payload = {
            "content": [
                {"type": "text", "text": '{"project":"X","task":"development","confidence":0.9,"reasoning":"r"}'}
            ],
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }
        client = ClaudeClient(api_key="test", client=_mock_client(payload))
        result = client.classify(SYSTEM_PROMPT, "test prompt")
        assert result.project == "X"
        assert result.task == "development"
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 20

    def test_classify_raises_on_http_error(self) -> None:
        bad = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
        client = ClaudeClient(api_key="test", client=bad)
        with pytest.raises(LLMError):
            client.classify(SYSTEM_PROMPT, "prompt")

    def test_extract_text_handles_missing_content(self) -> None:
        client = ClaudeClient(api_key="test", client=_mock_client({"usage": {}}))
        result = client.classify(SYSTEM_PROMPT, "prompt")
        # Missing content yields an empty parse — success=True with null fields.
        assert result.project is None
        assert result.task is None
        assert result.confidence == 0.0

    def test_classify_uses_default_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from chronolens.classification import claude_client as mod

        # Real httpx.Client backed by MockTransport, but no client was injected
        # — the production code path constructs `httpx.Client(timeout=…)` itself,
        # which we patch to return our pre-configured client.
        transport = httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                json={
                    "content": [
                        {
                            "type": "text",
                            "text": '{"project":null,"task":"admin","confidence":0.1,"reasoning":""}',
                        }
                    ],
                    "usage": {"input_tokens": 5, "output_tokens": 5},
                },
            )
        )
        real_client = httpx.Client(transport=transport)
        monkeypatch.setattr(mod.httpx, "Client", lambda **_kw: real_client)
        out = ClaudeClient(api_key="test").classify(SYSTEM_PROMPT, "user")
        assert out.task == "admin"


@pytest.mark.unit
class TestOpenAIClient:
    def test_classify_parses_response(self) -> None:
        payload = {
            "choices": [{"message": {"content": '{"project":"Y","task":"meeting","confidence":0.8,"reasoning":"r"}'}}],
            "usage": {"prompt_tokens": 80, "completion_tokens": 10},
        }
        client = OpenAIClient(api_key="test", client=_mock_client(payload))
        result = client.classify(SYSTEM_PROMPT, "prompt")
        assert result.project == "Y"
        assert result.task == "meeting"
        assert result.prompt_tokens == 80

    def test_classify_raises_on_http_error(self) -> None:
        bad = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(429)))
        client = OpenAIClient(api_key="test", client=bad)
        with pytest.raises(LLMError):
            client.classify(SYSTEM_PROMPT, "prompt")


@pytest.mark.unit
class TestPromptBuilder:
    def test_includes_projects(self) -> None:
        ctx = ClassificationContext(
            process_name="code.exe",
            redacted_title="main.py",
            redacted_ocr_text="def hello",
        )
        out = build_user_prompt(
            ctx,
            [ProjectChoice("Alpha", "Acme"), ProjectChoice("Beta")],
            ["development", "meeting"],
        )
        assert "Alpha" in out
        assert "Acme" in out
        assert "Beta" in out
        assert "development" in out
        assert "code.exe" in out

    def test_handles_no_active_projects(self) -> None:
        ctx = ClassificationContext(
            process_name="x.exe",
            redacted_title="t",
            redacted_ocr_text="y",
        )
        out = build_user_prompt(ctx, [], [])
        assert "no active projects" in out
