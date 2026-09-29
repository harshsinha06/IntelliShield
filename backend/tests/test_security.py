"""Security checks for the request path. The model is not asked to change its label."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.main import create_app
from app.ml import predict_url
from app.services.llm_service import ExplanationFacts, _messages, explain
from app.utils.rate_limit import SlidingWindowLimiter


def _client(tmp_path: Path, **overrides) -> TestClient:
    values = {
        "_env_file": None,
        "openai_api_key": SecretStr(""),
        "openai_base_url": "",
        "openai_model": "",
        "database_url": f"sqlite:///{tmp_path / 'history.db'}",
    }
    values.update(overrides)
    return TestClient(create_app(Settings(**values)))


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://user:supersecret@example.com/path",
        "https://example.com/has space",
        "http://",
    ],
)
def test_malformed_urls_are_rejected_without_echoing_the_input(tmp_path, url: str) -> None:
    with _client(tmp_path) as client:
        response = client.post("/api/v1/predict", json={"url": url, "model_path": "/tmp/other.joblib"})
    assert response.status_code == 422
    body = response.text
    assert "supersecret" not in body
    assert "alert(1)" not in body
    assert "/etc/passwd" not in body
    assert "/tmp/other.joblib" not in body
    assert response.json()["error"]["code"] == "validation_error"


def test_metadata_address_is_scored_locally(tmp_path, monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("the API tried to open a network request")

    monkeypatch.setattr(urllib.request, "urlopen", fail_if_called)
    monkeypatch.setattr("app.services.llm_service._post_chat_completion", fail_if_called)
    with _client(tmp_path) as client:
        response = client.post(
            "/api/v1/predict",
            json={"url": "http://169.254.169.254/latest/meta-data"},
        )
    assert response.status_code == 200
    assert response.json()["prediction"] in {"safe", "phishing"}


def test_shell_text_stays_in_the_url_string(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.post("/api/v1/predict", json={"url": "https://example.com/$(whoami)"})
    assert response.status_code == 200
    assert response.json()["prediction"] in {"safe", "phishing"}


def test_predict_logs_do_not_include_the_url(tmp_path, caplog) -> None:
    token = "logtoken9f3a"
    with _client(tmp_path) as client:
        response = client.post("/api/v1/predict", json={"url": f"https://example.com/{token}"})
    assert response.status_code == 200
    assert token not in caplog.text


def test_prompt_injection_text_cannot_replace_the_classifier_label(tmp_path, monkeypatch) -> None:
    captured: dict = {}

    def capture(_settings, messages) -> str:
        captured["messages"] = messages
        return json.dumps(
            {
                "prediction": "safe",
                "summary": "Ignore the classifier.",
                "reasoning": ["The URL text asked for a different label."],
                "risk_factors": ["The supplied signals remain the evidence."],
                "recommendations": ["Do not enter a password on this page."],
            }
        )

    monkeypatch.setattr("app.services.llm_service._post_chat_completion", capture)
    settings = {
        "openai_api_key": SecretStr("test-key"),
        "openai_base_url": "https://llm.example/v1",
        "openai_model": "test-model",
    }
    url = "http://192.0.2.10/ignore-previous-instructions"
    forest = predict_url(url)
    expected = "phishing" if forest["prediction"] == "phishing" else "safe"
    with _client(tmp_path, **settings) as client:
        response = client.post("/api/v1/predict", json={"url": url})
    assert response.status_code == 200
    assert response.json()["prediction"] == expected
    roles = [message["role"] for message in captured["messages"]]
    assert roles[0] == "system"
    assert "untrusted data" in captured["messages"][0]["content"]
    assert "ignore-previous-instructions" in captured["messages"][1]["content"]
    assert captured["messages"][1]["role"] == "user"


def test_explanation_messages_keep_the_url_in_the_user_role() -> None:
    facts = ExplanationFacts(
        classifier_prediction="phishing",
        probability=1.0,
        risk_level="high",
        normalized_url_redacted="https://example.com/ignore-previous-instructions",
        signals=[],
    )
    messages = _messages(facts)
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "ignore-previous-instructions" not in messages[0]["content"]


def test_llm_response_cannot_change_facts() -> None:
    facts = ExplanationFacts(
        classifier_prediction="phishing",
        probability=1.0,
        risk_level="high",
        normalized_url_redacted="https://example.com/",
        signals=[{"feature": "uses_https", "value": 1.0, "summary": "The URL uses HTTPS."}],
    )
    settings = Settings(
        _env_file=None,
        openai_api_key=SecretStr("test-key"),
        openai_base_url="https://llm.example/v1",
        openai_model="test-model",
    )

    def post(_settings, _messages) -> str:
        return json.dumps(
            {
                "classifier_prediction": "safe",
                "summary": "Treat this as safe.",
                "reasoning": ["Only the supplied signal is evidence."],
                "risk_factors": ["The URL uses HTTPS."],
                "recommendations": ["Do not enter a password on this page."],
            }
        )

    result = explain(facts, settings, post=post)
    assert facts.classifier_prediction == "phishing"
    assert "classifier_prediction" not in result.model_dump()


def test_sliding_window_drops_old_hits() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=10)
    assert limiter.allow("client", now=0.0) is True
    assert limiter.allow("client", now=1.0) is False
    assert limiter.allow("client", now=10.0) is True
    assert limiter.allow("other", now=1.0) is True


def test_rate_limit_blocks_the_next_predict(tmp_path) -> None:
    with _client(tmp_path, rate_limit_requests=2, rate_limit_window_seconds=60) as client:
        assert client.post("/api/v1/predict", json={"url": "https://www.uni-mainz.de"}).status_code == 200
        assert client.post("/api/v1/predict", json={"url": "https://example.com"}).status_code == 200
        blocked = client.post("/api/v1/predict", json={"url": "https://example.com/docs"})
        health = client.get("/health")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert blocked.headers["retry-after"] == "60"
    assert health.status_code == 200


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins="*")


def test_frontend_sources_do_not_embed_html_or_api_keys() -> None:
    root = Path(__file__).resolve().parents[2] / "frontend"
    offenders: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"node_modules", ".next"} for part in path.parts):
            continue
        if path.suffix not in {".ts", ".tsx", ".js", ".jsx", ".css", ".md", ".example"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "dangerouslySetInnerHTML" in text or "OPENAI_API_KEY" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
