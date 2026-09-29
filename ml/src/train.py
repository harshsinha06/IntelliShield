"""Train the IntelliShield Random Forest and write the model bundle.

Protocol, fixed before looking at test scores:

* Preprocess with src.preprocessing (dedupe, then stratified 70/15/15).
* Fit each grid candidate on the training split only.
* Choose the candidate with the highest phishing-class F1 on the validation
  split. Ties prefer smaller max_depth, then fewer trees, then a larger
  min_samples_leaf.
* Refit those hyperparameters on train+validation.
* Score the refit model once on the test split.
* Save the refit model, feature_config.json, and metrics.json.

The test split is not used to choose hyperparameters.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier

from src.data_loader import load_raw_dataset
from src.evaluate import (
    METRICS_PATH,
    MODEL_PATH,
    SPLITS_PATH,
    feature_importance_table,
    format_metrics,
    score_model,
)
from src.feature_extractor import FEATURE_SPEC_VERSION, feature_config
from src.preprocessing import feature_matrix, run_preprocessing_pipeline

FIXED_PARAMS = {
    "criterion": "gini",
    "max_features": "sqrt",
    "bootstrap": True,
    "class_weight": None,
    "random_state": 42,
    "n_jobs": -1,
}

PARAM_GRID = (
    {"n_estimators": 100, "max_depth": 20, "min_samples_leaf": 2},
    {"n_estimators": 200, "max_depth": 20, "min_samples_leaf": 2},
    {"n_estimators": 100, "max_depth": 30, "min_samples_leaf": 2},
    {"n_estimators": 200, "max_depth": 30, "min_samples_leaf": 2},
    {"n_estimators": 100, "max_depth": 20, "min_samples_leaf": 5},
    {"n_estimators": 200, "max_depth": 20, "min_samples_leaf": 5},
)


def select_hyperparameters(train_df: pd.DataFrame, val_df: pd.DataFrame) -> dict:
    """Return the winning parameters and the validation score of each candidate."""
    train_x = feature_matrix(train_df)
    train_y = train_df["label"].to_numpy()
    best: dict | None = None
    results = []
    for params in PARAM_GRID:
        print(f"fitting {params}", flush=True)
        model = RandomForestClassifier(**FIXED_PARAMS, **params)
        model.fit(train_x, train_y)
        metrics = score_model(model, val_df)
        record = {
            "params": params,
            "validation_f1": metrics["f1"],
            "validation_metrics": metrics,
        }
        results.append(record)
        print(format_metrics(f"Validation for {params}", metrics), flush=True)
        if best is None or _candidate_rank(record) > _candidate_rank(best):
            best = record
        del model
    if best is None:
        raise RuntimeError("Hyperparameter search produced no model.")
    return {"selected": best, "candidates": results}


def refit_model(train_df: pd.DataFrame, val_df: pd.DataFrame, params: dict) -> RandomForestClassifier:
    combined = pd.concat([train_df, val_df], ignore_index=True)
    model = RandomForestClassifier(**FIXED_PARAMS, **params)
    model.fit(feature_matrix(combined), combined["label"].to_numpy())
    return model


def save_artifacts(
    model,
    dataset_report: dict,
    cleaning_report: dict,
    selection: dict,
    validation_metrics: dict,
    test_metrics: dict,
) -> None:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPLITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = feature_config()
    config_path = MODEL_PATH.parent / "feature_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    selected_params = selection["selected"]["params"]
    payload = {
        "feature_spec_version": FEATURE_SPEC_VERSION,
        "dataset": dataset_report,
        "preprocessing": cleaning_report,
        "fixed_hyperparameters": FIXED_PARAMS,
        "selected_hyperparameters": selected_params,
        "validation_metrics_before_refit": validation_metrics,
        "test_metrics": test_metrics,
        "feature_importances": feature_importance_table(model),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "grid": [
            {
                "params": item["params"],
                "validation_f1": item["validation_f1"],
                "validation_metrics": item["validation_metrics"],
            }
            for item in selection["candidates"]
        ],
    }
    bundle = {
        "model": model,
        "feature_config": config,
        "selected_hyperparameters": selected_params,
        "fixed_hyperparameters": FIXED_PARAMS,
        "sklearn_version": sklearn.__version__,
        "feature_spec_version": FEATURE_SPEC_VERSION,
    }
    joblib.dump(bundle, MODEL_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(_jsonable(payload), indent=2) + "\n", encoding="utf-8")


def save_splits(train_df, val_df, test_df, dataset_report: dict) -> None:
    SPLITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "train": train_df,
            "validation": val_df,
            "test": test_df,
            "sha256": dataset_report["sha256"],
            "feature_spec_version": FEATURE_SPEC_VERSION,
        },
        SPLITS_PATH,
        compress=3,
    )


def train() -> dict:
    raw, dataset_report = load_raw_dataset()
    print(json.dumps(_jsonable(dataset_report), indent=2), flush=True)
    train_df, val_df, test_df, cleaning_report = run_preprocessing_pipeline(raw, progress=True)
    print(
        "split sizes",
        {
            "train": len(train_df),
            "validation": len(val_df),
            "test": len(test_df),
        },
        flush=True,
    )
    save_splits(train_df, val_df, test_df, dataset_report)
    selection = select_hyperparameters(train_df, val_df)
    selected_params = selection["selected"]["params"]
    validation_metrics = selection["selected"]["validation_metrics"]
    print(f"selected hyperparameters: {selected_params}", flush=True)
    model = refit_model(train_df, val_df, selected_params)
    test_metrics = score_model(model, test_df)
    print(format_metrics("Test set (saved model)", test_metrics), flush=True)
    save_artifacts(
        model,
        dataset_report,
        cleaning_report,
        selection,
        validation_metrics,
        test_metrics,
    )
    print("feature importances:", flush=True)
    for row in feature_importance_table(model):
        print(f"  {row['feature']}: {row['importance']:.4f}", flush=True)
    print(f"saved {MODEL_PATH}", flush=True)
    return {"test_metrics": test_metrics, "selected_hyperparameters": selected_params}


def _candidate_rank(record: dict) -> tuple:
    params = record["params"]
    return (
        record["validation_f1"],
        -int(params["max_depth"]),
        -int(params["n_estimators"]),
        int(params["min_samples_leaf"]),
    )


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        return value.item()
    return value


def main() -> None:
    train()


if __name__ == "__main__":
    main()
