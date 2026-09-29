"""Explanation tests. The language-model HTTP call is mocked."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.services.llm_service import (
    ExplanationFacts,
    build_facts,
    explain,
    redact_url,
)


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "openai_api_key": SecretStr("test-key"),
        "openai_base_url": "https://llm.example/v1",
        "openai_model": "test-model",
        "llm_timeout_seconds": 7.5,
    }
    values.update(overrides)
    return Settings(**values)


def _facts() -> ExplanationFacts:
    return build_facts(
        prediction="phishing",
        probability=1.0,
        risk_level="high",
        normalized_url="https://user:supersecret@evil.example/login?token=supersecret",
        signals=[
            SimpleNamespace(feature="uses_https", value=0.0, summary="The URL uses HTTP."),
        ],
    )


def _valid_content(**extra) -> str:
    body = {
        "summary": "The classifier labeled this URL phishing.",
        "reasoning": ["The URL uses HTTP."],
        "risk_factors": ["The hostname measurement was supplied by the classifier."],
        "recommendations": ["Do not enter a password on this page."],
    }
    body.update(extra)
    return json.dumps(body)


def test_redact_url_removes_userinfo_and_query_values() -> None:
    redacted = redact_url("https://user:secret@example.com/a?token=abc&next=1")
    assert "secret" not in redacted
    assert "abc" not in redacted
    assert redacted.startswith("https://REDACTED@example.com/a?")
    assert "token=REDACTED" in redacted
    assert "next=REDACTED" in redacted


def test_missing_credentials_skip_the_network(monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("the explanation client tried to open a connection")

    monkeypatch.setattr(httpx, "Client", fail_if_called)
    settings = _settings(openai_api_key=SecretStr(""), openai_base_url="", openai_model="")
    result = explain(_facts(), settings)
    assert result.source == "fallback"
    assert "classifier labeled this URL phishing" in result.summary


def test_mocked_completion_is_validated_and_does_not_carry_a_label() -> None:
    seen: dict = {}

    def post(settings: Settings, messages: list[dict[str, str]]) -> str:
        seen["messages"] = messages
        return _valid_content(prediction="safe", classifier_prediction="safe")

    result = explain(_facts(), _settings(), post=post)
    payload = json.dumps(seen["messages"])
    assert "supersecret" not in payload
    assert "REDACTED" in payload
    assert result.source == "llm"
    assert "prediction" not in result.model_dump()
    assert result.summary == "The classifier labeled this URL phishing."
    assert result.reasoning == ["The URL uses HTTP."]


def test_markdown_fence_is_accepted() -> None:
    def post(_settings, _messages) -> str:
        return "```json\n" + _valid_content() + "\n```"

    result = explain(_facts(), _settings(), post=post)
    assert result.source == "llm"


@pytest.mark.parametrize(
    "content",
    ["not-json", json.dumps({"summary": "x"}), json.dumps(["not", "an", "object"])],
)
def test_invalid_model_json_uses_the_fallback(content: str) -> None:
    result = explain(_facts(), _settings(), post=lambda _settings, _messages: content)
    assert result.source == "fallback"
    assert result.reasoning == ["The URL uses HTTP."]


def test_timeout_uses_the_fallback() -> None:
    def post(_settings, _messages) -> str:
        raise httpx.TimeoutException("timed out")

    result = explain(_facts(), _settings(), post=post)
    assert result.source == "fallback"
    assert "language-model explanation was unavailable" in result.summary


def test_http_error_uses_the_fallback() -> None:
    def post(_settings, _messages) -> str:
        raise httpx.ConnectError("connection failed")

    result = explain(_facts(), _settings(), post=post)
    assert result.source == "fallback"


def test_chat_client_sends_only_facts_and_applies_the_timeout(monkeypatch) -> None:
    seen: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": _valid_content()}}]}

    class FakeClient:
        def __init__(self, timeout) -> None:
            seen["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> bool:
            return False

        def post(self, endpoint, json, headers) -> FakeResponse:
            seen["endpoint"] = endpoint
            seen["headers"] = headers
            seen["body"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    result = explain(_facts(), _settings())
    assert result.source == "llm"
    assert seen["endpoint"] == "https://llm.example/v1/chat/completions"
    assert seen["timeout"] == httpx.Timeout(7.5)
    assert seen["headers"]["Authorization"] == "Bearer test-key"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["temperature"] == 0.2
    user_text = seen["body"]["messages"][1]["content"]
    assert "supersecret" not in user_text
    assert "classifier_prediction" in user_text
    assert "test-key" not in user_text
