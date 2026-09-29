"""Import the trained pipeline from the ml package without copying it."""

from __future__ import annotations

import sys
from pathlib import Path

from app.config import REPO_ROOT

_ML_ROOT = REPO_ROOT / "ml"
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

from src.feature_extractor import FEATURE_NAMES, MAX_URL_LENGTH, extract_features
from src.predict import predict_url

__all__ = [
    "FEATURE_NAMES",
    "MAX_URL_LENGTH",
    "extract_features",
    "predict_url",
]
