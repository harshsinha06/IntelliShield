"""Lock the saved evaluation record. These numbers are read from metrics.json."""

from __future__ import annotations

import json
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ML_ROOT / "models" / "metrics.json"


def test_saved_split_has_no_url_overlap() -> None:
    payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    overlap = payload["preprocessing"]["split"]["url_overlap"]
    assert overlap == {"train_validation": 0, "train_test": 0, "validation_test": 0}


def test_saved_test_confusion_counts() -> None:
    payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    matrix = payload["test_metrics"]["confusion_matrix"]
    assert matrix["true_legitimate_predicted_phishing"] == 13
    assert matrix["true_phishing_predicted_legitimate"] == 86
    assert matrix["true_legitimate_predicted_legitimate"] == 20215
    assert matrix["true_phishing_predicted_phishing"] == 14959
    assert payload["test_metrics"]["precision"] == 0.9991317125300561
    assert payload["test_metrics"]["recall"] == 0.9942838152210036


def test_class_weight_was_not_applied() -> None:
    payload = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    assert payload["fixed_hyperparameters"]["class_weight"] is None
    cleaned = payload["preprocessing"]["cleaned_class_counts"]
    assert cleaned == {"legitimate": 134850, "phishing": 100302}
