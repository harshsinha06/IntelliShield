"""Score one URL with the saved Random Forest and the shared extractor."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from src.feature_extractor import FEATURE_NAMES, feature_config, extract_features

ML_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = ML_ROOT / "models" / "phishing_rf.joblib"
DEFAULT_CONFIG_PATH = ML_ROOT / "models" / "feature_config.json"

LABEL_NAMES = {0: "legitimate", 1: "phishing"}


def predict_url(
    url: str,
    model_path: Path | None = None,
    config_path: Path | None = None,
) -> dict:
    """Extract features, score the URL, and return the prediction payload.

    A malformed URL returns prediction=None and an error code. A missing
    model file raises FileNotFoundError.
    """
    extraction = extract_features(url)
    if not extraction.ok or extraction.features is None:
        return {
            "input_url": url if isinstance(url, str) else None,
            "normalized_url": None,
            "prediction": None,
            "phishing_probability": None,
            "legitimate_probability": None,
            "features": None,
            "error": extraction.error,
        }

    model_file = Path(model_path) if model_path is not None else DEFAULT_MODEL_PATH
    config_file = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    if not model_file.exists():
        raise FileNotFoundError(
            f"Missing model at {model_file}. Train it with: python -m src.train"
        )
    if not config_file.exists():
        raise FileNotFoundError(
            f"Missing feature config at {config_file}. Train it with: python -m src.train"
        )

    config = _load_config(str(config_file.resolve()), config_file.stat().st_mtime_ns)
    _assert_config_matches_extractor(config)
    bundle = _load_bundle(str(model_file.resolve()), model_file.stat().st_mtime_ns)
    model = bundle["model"]
    _assert_model_matches_config(model, config)

    names = config["feature_names"]
    row = pd.DataFrame([[extraction.features[name] for name in names]], columns=names)
    class_list = [int(label) for label in model.classes_]
    probabilities = model.predict_proba(row)[0]
    predicted = int(model.predict(row)[0])
    phishing_probability = float(probabilities[class_list.index(1)])
    legitimate_probability = float(probabilities[class_list.index(0)])
    return {
        "input_url": url,
        "normalized_url": extraction.normalized_url,
        "prediction": LABEL_NAMES[predicted],
        "phishing_probability": phishing_probability,
        "legitimate_probability": legitimate_probability,
        "features": {name: extraction.features[name] for name in names},
        "error": None,
    }


def _assert_config_matches_extractor(config: dict) -> None:
    current = feature_config()
    for key in ("feature_spec_version", "feature_names", "keyword_lexicon", "shorteners"):
        if config.get(key) != current[key]:
            raise ValueError(
                f"Saved feature config {key!r} does not match the extractor. Retrain."
            )
    if config["feature_names"] != list(FEATURE_NAMES):
        raise ValueError("Feature order in the saved config does not match FEATURE_NAMES.")


def _assert_model_matches_config(model, config: dict) -> None:
    names = list(getattr(model, "feature_names_in_", []))
    if names != config["feature_names"]:
        raise ValueError("Model feature order does not match feature_config.json.")
    classes = {int(label) for label in model.classes_}
    if classes != {0, 1}:
        raise ValueError(f"Unexpected model classes: {sorted(classes)}")


@lru_cache(maxsize=4)
def _load_bundle(path: str, _mtime_ns: int):
    return joblib.load(path)


@lru_cache(maxsize=4)
def _load_config(path: str, _mtime_ns: int) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m src.predict <url>")
    print(json.dumps(predict_url(sys.argv[1]), indent=2))


if __name__ == "__main__":
    main()
