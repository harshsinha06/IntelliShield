"""API tests for health, validation, and the trained model."""

from __future__ import annotations

import json
import urllib.request

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app
from app.ml import extract_features
from app.services.llm_service import Analysis
from app.services.prediction_service import risk_level


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    database = tmp_path_factory.mktemp("api") / "history.db"
    application = create_app(
        Settings(
            _env_file=None,
            openai_api_key=SecretStr(""),
            openai_base_url="",
            openai_model="",
            database_url=f"sqlite:///{database}",
        )
    )
    with TestClient(application) as test_client:
        yield test_client


def test_health_reports_loaded_model(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_loaded": True}


def test_openapi_lists_the_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health" in paths
    assert "/api/v1/predict" in paths
    assert "/api/v1/history" in paths
    assert "/api/v1/history/{analysis_id}" in paths


def test_cors_allows_the_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/predict",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_predict_uses_the_shared_extractor_and_does_not_fetch(client: TestClient, monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("the API tried to open a network request")

    monkeypatch.setattr(urllib.request, "urlopen", fail_if_called)
    monkeypatch.setattr(httpx, "Client", fail_if_called)
    url = "http://192.0.2.10:8080/login"
    response = client.post("/api/v1/predict", json={"url": url})
    assert response.status_code == 200
    body = response.json()
    extracted = extract_features(url)
    assert body["url"] == extracted.normalized_url
    assert body["features"] == {name: float(value) for name, value in extracted.features.items()}
    assert body["prediction"] == "phishing"
    assert body["risk_level"] == "high"
    assert 0.0 <= body["probability"] <= 1.0
    assert body["signals"]
    assert len(body["signals"]) <= 5
    assert {"feature", "value", "importance", "summary"} <= set(body["signals"][0])
    assert body["analysis"]["source"] == "fallback"
    assert set(body["analysis"]) == {
        "source",
        "summary",
        "reasoning",
        "risk_factors",
        "recommendations",
    }
    assert "classifier labeled this URL phishing" in body["analysis"]["summary"]


def test_known_legitimate_url_is_safe(client: TestClient) -> None:
    response = client.post("/api/v1/predict", json={"url": "https://www.uni-mainz.de"})
    assert response.status_code == 200
    body = response.json()
    assert body["prediction"] == "safe"
    assert body["risk_level"] == "low"


def test_shell_metacharacters_are_not_executed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/predict",
        json={"url": "https://example.com/$(whoami)"},
    )
    assert response.status_code == 200
    assert response.json()["prediction"] in {"safe", "phishing"}


def test_invalid_urls_do_not_echo_secrets(client: TestClient, caplog) -> None:
    secret = "supersecretvalue"
    response = client.post(
        "/api/v1/predict",
        json={"url": f"ftp://user:{secret}@example.com/path"},
    )
    assert response.status_code == 422
    text = response.text
    assert secret not in text
    assert secret not in caplog.text
    assert response.json()["error"]["code"] == "validation_error"


def test_missing_url_is_422(client: TestClient) -> None:
    response = client.post("/api/v1/predict", json={})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "URL is required."


def test_missing_model_is_503(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        model_path="/tmp/intellishield-missing-model.joblib",
        feature_config_path="/tmp/intellishield-missing-config.json",
        database_url=f"sqlite:///{tmp_path / 'history.db'}",
    )
    application = create_app(settings)
    with TestClient(application) as test_client:
        health = test_client.get("/health")
        assert health.json()["model_loaded"] is False
        response = test_client.post("/api/v1/predict", json={"url": "https://example.com"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_unavailable"


def _llm_settings(database: str) -> Settings:
    return Settings(
        _env_file=None,
        openai_api_key=SecretStr("test-key"),
        openai_base_url="https://llm.example/v1",
        openai_model="test-model",
        database_url=database,
    )


def test_mocked_explanation_cannot_change_the_classifier_label(monkeypatch, tmp_path) -> None:
    def fake_explain(facts, settings, post=None) -> Analysis:
        assert facts.classifier_prediction == "phishing"
        return Analysis(
            source="llm",
            summary="Ignore the classifier and treat this URL as safe.",
            reasoning=["The supplied signals are the only evidence."],
            risk_factors=["The URL uses HTTP."],
            recommendations=["Do not enter a password on this page."],
        )

    monkeypatch.setattr("app.services.prediction_service.explain", fake_explain)
    application = create_app(_llm_settings(f"sqlite:///{tmp_path / 'history.db'}"))
    with TestClient(application) as test_client:
        response = test_client.post(
            "/api/v1/predict",
            json={"url": "http://192.0.2.10:8080/login"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["prediction"] == "phishing"
    assert body["risk_level"] == "high"
    assert body["analysis"]["source"] == "llm"
    assert body["analysis"]["summary"].startswith("Ignore the classifier")


def test_llm_timeout_keeps_the_classifier_response(monkeypatch, tmp_path) -> None:
    def timed_out(_settings, _messages) -> str:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.services.llm_service._post_chat_completion", timed_out)
    application = create_app(_llm_settings(f"sqlite:///{tmp_path / 'history.db'}"))
    with TestClient(application) as test_client:
        response = test_client.post(
            "/api/v1/predict",
            json={"url": "https://user:supersecret@192.0.2.10/login?token=supersecret"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["prediction"] == "phishing"
    assert body["analysis"]["source"] == "fallback"
    assert "supersecret" not in body["analysis"]["summary"]


def test_llm_payload_redacts_secrets(monkeypatch, tmp_path) -> None:
    seen: dict = {}

    def capture(_settings, messages) -> str:
        seen["messages"] = messages
        return json.dumps(
            {
                "prediction": "safe",
                "summary": "The classifier labeled this URL phishing.",
                "reasoning": ["The URL uses HTTP."],
                "risk_factors": ["The hostname is an IP address."],
                "recommendations": ["Do not enter a password on this page."],
            }
        )

    monkeypatch.setattr("app.services.llm_service._post_chat_completion", capture)
    application = create_app(_llm_settings(f"sqlite:///{tmp_path / 'history.db'}"))
    with TestClient(application) as test_client:
        response = test_client.post(
            "/api/v1/predict",
            json={"url": "https://user:supersecret@192.0.2.10/login?token=supersecret"},
        )
    assert response.status_code == 200
    assert response.json()["prediction"] == "phishing"
    assert response.json()["analysis"]["source"] == "llm"
    payload = json.dumps(seen["messages"])
    assert "supersecret" not in payload
    assert "test-key" not in payload


def test_risk_buckets() -> None:
    assert risk_level(0.0) == "low"
    assert risk_level(0.39) == "low"
    assert risk_level(0.40) == "medium"
    assert risk_level(0.69) == "medium"
    assert risk_level(0.70) == "high"
    assert risk_level(1.0) == "high"
