"""Signals derived from the shared extractor output and saved importances.

This module does not recompute URL features. It formats values that
`extract_features` already produced and ranks them with the importances
stored in metrics.json.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.ml import FEATURE_NAMES, extract_features
from app.schemas.predict import Signal
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_SIGNALS = 5

# Binary states worth showing even when their global importance is small.
_ACTIVE_INDICATORS: tuple[tuple[str, int], ...] = (
    ("has_ip_address", 1),
    ("has_at_symbol", 1),
    ("is_url_shortener", 1),
    ("has_suspicious_keyword", 1),
    ("uses_https", 0),
)


def extract(url: str):
    """Delegate to the training extractor."""
    return extract_features(url)


def load_importances(metrics_path: Path) -> dict[str, float]:
    if not metrics_path.exists():
        logger.warning("feature importance file is missing")
        return {}
    return _load_importances_cached(str(metrics_path.resolve()), metrics_path.stat().st_mtime_ns)


def build_signals(features: dict[str, int], importances: dict[str, float]) -> list[Signal]:
    """Return at most five signals, ordered by saved global importance."""
    chosen: list[str] = []
    for name, active_value in _ACTIVE_INDICATORS:
        if features.get(name) == active_value:
            chosen.append(name)
    ranked = sorted(
        (name for name in FEATURE_NAMES if name in features),
        key=lambda name: importances.get(name, 0.0),
        reverse=True,
    )
    for name in ranked:
        if name not in chosen:
            chosen.append(name)
        if len(chosen) >= MAX_SIGNALS:
            break
    chosen = chosen[:MAX_SIGNALS]
    chosen.sort(key=lambda name: importances.get(name, 0.0), reverse=True)
    return [
        Signal(
            feature=name,
            value=float(features[name]),
            importance=float(importances.get(name, 0.0)),
            summary=summarize(name, features[name]),
        )
        for name in chosen
    ]


def summarize(name: str, value: int) -> str:
    if name == "uses_https":
        return "The URL uses HTTPS." if value else "The URL uses HTTP."
    if name == "has_ip_address":
        return "The hostname is an IP address." if value else "The hostname is not an IP address."
    if name == "has_at_symbol":
        return "The URL contains an @ character." if value else "The URL does not contain an @ character."
    if name == "is_url_shortener":
        return (
            "The hostname is on the known shortener list."
            if value
            else "The hostname is not on the known shortener list."
        )
    if name == "has_suspicious_keyword":
        return (
            "The URL contains a token from the suspicious-keyword list."
            if value
            else "The URL does not contain a suspicious-keyword token."
        )
    labels = {
        "url_length": "The normalized URL is {value} characters long.",
        "hostname_length": "The hostname is {value} characters long.",
        "domain_length": "The domain-length measurement is {value}.",
        "dot_count": "The URL contains {value} dots.",
        "subdomain_count": "The subdomain count is {value}.",
        "hyphen_count": "The URL contains {value} hyphens.",
        "special_char_count": "The URL contains {value} non-alphanumeric characters.",
        "digit_count": "The URL contains {value} digits.",
        "path_segment_count": "The path has {value} segments.",
        "query_param_count": "The URL has {value} query parameters.",
    }
    template = labels.get(name, "{name} is {value}.")
    return template.format(name=name, value=value)


@lru_cache(maxsize=4)
def _load_importances_cached(path: str, _mtime_ns: int) -> dict[str, float]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("feature_importances", [])
    return {str(row["feature"]): float(row["importance"]) for row in rows}
