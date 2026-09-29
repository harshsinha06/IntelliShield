"""History is written only for a completed score, and secrets are not stored."""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app
from app.services.llm_service import redact_url


def _client(tmp_path) -> TestClient:
    settings = Settings(
        _env_file=None,
        openai_api_key=SecretStr(""),
        openai_base_url="",
        openai_model="",
        database_url=f"sqlite:///{tmp_path / 'history.db'}",
    )
    return TestClient(create_app(settings))


def test_startup_does_not_store_the_warmup_url(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.get("/api/v1/history")
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_successful_score_is_listed_and_can_be_opened(tmp_path) -> None:
    secret_url = "https://user:supersecret@192.0.2.10/login?token=supersecret"
    with _client(tmp_path) as client:
        first = client.post("/api/v1/predict", json={"url": "https://www.uni-mainz.de"})
        second = client.post("/api/v1/predict", json={"url": "http://192.0.2.10:8080/login"})
        secret = client.post("/api/v1/predict", json={"url": secret_url})
        assert first.status_code == 200
        assert second.status_code == 200
        assert secret.status_code == 200
        listed = client.get("/api/v1/history")
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert [item["prediction"] for item in items[1:]] == ["phishing", "safe"]
        latest = items[0]
        assert latest["url"] == redact_url(secret.json()["url"])
        assert "supersecret" not in latest["url"]
        assert latest["risk_level"] == secret.json()["risk_level"]
        assert latest["probability"] == secret.json()["probability"]
        assert latest["created_at"].endswith("Z") or latest["created_at"].endswith("+00:00")
        detail = client.get(f"/api/v1/history/{items[1]['id']}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["prediction"] == "phishing"
        assert body["risk_level"] == "high"
        assert body["features"] == second.json()["features"]
        assert body["signals"] == second.json()["signals"]
        assert body["analysis"] == second.json()["analysis"]
        assert "supersecret" not in listed.text
        assert "supersecret" not in detail.text


def test_rejected_url_is_not_stored(tmp_path) -> None:
    with _client(tmp_path) as client:
        rejected = client.post("/api/v1/predict", json={"url": "ftp://example.com/file"})
        assert rejected.status_code == 422
        history = client.get("/api/v1/history")
    assert history.json()["items"] == []


def test_missing_analysis_is_404(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.get("/api/v1/history/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_history_id_must_be_an_integer(tmp_path) -> None:
    with _client(tmp_path) as client:
        response = client.get("/api/v1/history/not-a-number")
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Analysis id must be an integer."


def test_limit_returns_the_newest_rows(tmp_path) -> None:
    with _client(tmp_path) as client:
        client.post("/api/v1/predict", json={"url": "https://www.uni-mainz.de"})
        client.post("/api/v1/predict", json={"url": "http://192.0.2.10:8080/login"})
        response = client.get("/api/v1/history", params={"limit": 1})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["prediction"] == "phishing"
