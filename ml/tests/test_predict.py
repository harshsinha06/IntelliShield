"""Prediction interface, using a tiny forest so the test does not need the real model."""

import json

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from src.feature_extractor import FEATURE_NAMES, extract_features, feature_config
from src.predict import predict_url
from src.preprocessing import feature_matrix


def test_predict_url_returns_features_probabilities_and_a_label(tmp_path):
    rows = []
    for index in range(25):
        legit = extract_features(f"https://docs{index}.example.com/guide")
        phish = extract_features(f"http://login{index}.example.net/login?next={index}")
        rows.append({"label": 0, **legit.features})
        rows.append({"label": 1, **phish.features})
    frame = pd.DataFrame(rows)
    model = RandomForestClassifier(n_estimators=20, max_depth=6, random_state=42)
    model.fit(feature_matrix(frame), frame["label"])

    model_path = tmp_path / "phishing_rf.joblib"
    config_path = tmp_path / "feature_config.json"
    import joblib

    joblib.dump({"model": model}, model_path)
    config_path.write_text(json.dumps(feature_config()), encoding="utf-8")

    url = "https://example.com/docs/guide"
    result = predict_url(url, model_path=model_path, config_path=config_path)
    extracted = extract_features(url)
    assert result["error"] is None
    assert result["prediction"] in {"legitimate", "phishing"}
    assert result["features"] == extracted.features
    assert list(result["features"]) == list(FEATURE_NAMES)
    assert abs(result["phishing_probability"] + result["legitimate_probability"] - 1) < 1e-6
    assert 0.0 <= result["phishing_probability"] <= 1.0

    malformed = predict_url("notaurl", model_path=model_path, config_path=config_path)
    assert malformed["prediction"] is None
    assert malformed["features"] is None
    assert malformed["error"] == "scheme_must_be_http_or_https"
