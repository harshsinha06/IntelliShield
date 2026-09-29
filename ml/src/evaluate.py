"""Score a fitted classifier. This module does not train."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.feature_extractor import FEATURE_NAMES
from src.preprocessing import feature_matrix

ML_ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ML_ROOT / "models" / "metrics.json"
MODEL_PATH = ML_ROOT / "models" / "phishing_rf.joblib"
SPLITS_PATH = ML_ROOT / "data" / "processed" / "splits.joblib"

PHISHING = 1


def score_model(model, frame) -> dict:
    """Score one partition. Positive class is phishing (label 1)."""
    features = feature_matrix(frame)
    labels = frame["label"].to_numpy()
    predicted = model.predict(features)
    probabilities = model.predict_proba(features)
    class_list = [int(label) for label in model.classes_]
    if PHISHING not in class_list:
        raise ValueError(f"Model classes do not include phishing: {class_list}")
    phishing_probability = probabilities[:, class_list.index(PHISHING)]
    matrix = confusion_matrix(labels, predicted, labels=[0, 1])
    true_negative, false_positive, false_negative, true_positive = (
        int(value) for value in matrix.ravel()
    )
    return {
        "positive_class": "phishing",
        "accuracy": float(accuracy_score(labels, predicted)),
        "precision": float(precision_score(labels, predicted, pos_label=PHISHING, zero_division=0)),
        "recall": float(recall_score(labels, predicted, pos_label=PHISHING, zero_division=0)),
        "f1": float(f1_score(labels, predicted, pos_label=PHISHING, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, phishing_probability)),
        "support": {
            "legitimate": int(np.sum(labels == 0)),
            "phishing": int(np.sum(labels == 1)),
        },
        "confusion_matrix": {
            "row_order": ["true_legitimate", "true_phishing"],
            "column_order": ["predicted_legitimate", "predicted_phishing"],
            "values": [
                [true_negative, false_positive],
                [false_negative, true_positive],
            ],
            "true_legitimate_predicted_legitimate": true_negative,
            "true_legitimate_predicted_phishing": false_positive,
            "true_phishing_predicted_legitimate": false_negative,
            "true_phishing_predicted_phishing": true_positive,
        },
    }


def feature_importance_table(model) -> list[dict]:
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        raise ValueError("Model has no feature_importances_.")
    names = list(getattr(model, "feature_names_in_", FEATURE_NAMES))
    if list(names) != list(FEATURE_NAMES):
        raise ValueError("Model feature order does not match the extractor.")
    ranked = sorted(
        (
            {"feature": name, "importance": float(score)}
            for name, score in zip(names, importances)
        ),
        key=lambda item: (-item["importance"], item["feature"]),
    )
    return ranked


def format_metrics(title: str, metrics: dict) -> str:
    matrix = metrics["confusion_matrix"]["values"]
    return "\n".join(
        [
            title,
            f"  Accuracy:  {metrics['accuracy']:.4f}",
            f"  Precision: {metrics['precision']:.4f}  (positive class: phishing)",
            f"  Recall:    {metrics['recall']:.4f}  (positive class: phishing)",
            f"  F1-score:  {metrics['f1']:.4f}  (positive class: phishing)",
            f"  ROC-AUC:   {metrics['roc_auc']:.4f}",
            "  Confusion matrix [rows true legitimate, true phishing; columns predicted legitimate, predicted phishing]:",
            f"    {matrix[0]}",
            f"    {matrix[1]}",
            f"  Support: legitimate={metrics['support']['legitimate']} phishing={metrics['support']['phishing']}",
        ]
    )


def load_metrics(path: Path = METRICS_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    import joblib

    if not MODEL_PATH.exists():
        raise SystemExit(f"Missing model at {MODEL_PATH}. Train first: python -m src.train")
    if not SPLITS_PATH.exists():
        raise SystemExit(f"Missing splits at {SPLITS_PATH}. Train first: python -m src.train")

    bundle = joblib.load(MODEL_PATH)
    splits = joblib.load(SPLITS_PATH)
    model = bundle["model"]
    names = list(getattr(model, "feature_names_in_", []))
    if names != list(FEATURE_NAMES):
        raise SystemExit("Saved model feature order does not match the extractor.")

    test_metrics = score_model(model, splits["test"])
    print(format_metrics("Test set (saved model, rescored)", test_metrics))
    if METRICS_PATH.exists():
        saved = load_metrics()
        saved_test = saved.get("test_metrics", {})
        comparable = ("accuracy", "precision", "recall", "f1", "roc_auc")
        drift = [
            key
            for key in comparable
            if key in saved_test and abs(saved_test[key] - test_metrics[key]) > 1e-8
        ]
        if drift:
            print(f"Rescored test metrics differ from metrics.json on: {drift}")
        else:
            print("Rescored test metrics match metrics.json.")


if __name__ == "__main__":
    main()
