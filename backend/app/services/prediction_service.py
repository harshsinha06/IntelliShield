"""Score one URL with the saved forest.

The submitted string is passed only to the lexical extractor. This module
does not open a socket to that host and does not pass the string to a shell.
"""

from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.ml import predict_url
from app.schemas.predict import Analysis, PredictResponse
from app.services.feature_service import build_signals, load_importances
from app.services.llm_service import build_facts, explain, fallback_analysis
from app.utils.errors import APIError
from app.utils.logging import get_logger

logger = get_logger(__name__)

_LOW_BELOW = 0.40
_HIGH_FROM = 0.70

_URL_MESSAGES = {
    "url_empty": "URL is required.",
    "url_too_long": "URL must be at most 16384 characters.",
    "url_has_whitespace_or_control_character": "URL must not contain whitespace or control characters.",
    "url_unparseable": "URL could not be parsed.",
    "scheme_must_be_http_or_https": "URL scheme must be http or https.",
    "hostname_missing": "URL must include a hostname.",
    "hostname_idna_failed": "Hostname could not be encoded.",
    "hostname_invalid": "Hostname could not be parsed.",
    "url_must_be_string": "URL must be a string.",
    "feature_spec_incomplete": "URL could not be parsed.",
}


def risk_level(phishing_probability: float) -> str:
    """Map the phishing-class probability onto a display bucket.

    The cut points are API labels, not thresholds the forest was trained with.
    """
    if phishing_probability < _LOW_BELOW:
        return "low"
    if phishing_probability < _HIGH_FROM:
        return "medium"
    return "high"


def score(url: str, settings: Settings) -> PredictResponse:
    try:
        result = predict_url(
            url,
            model_path=settings.resolved_model_path,
            config_path=settings.resolved_feature_config_path,
        )
    except FileNotFoundError:
        logger.error("model files are missing")
        raise APIError("The detection model is not loaded.", 503, "model_unavailable") from None
    except ValueError:
        logger.error("model feature configuration does not match the extractor")
        raise APIError("The detection model is not loaded.", 503, "model_unavailable") from None

    if result.get("error"):
        code = str(result["error"])
        raise APIError(_URL_MESSAGES.get(code, "URL could not be parsed."), 422, "validation_error")

    features = result["features"]
    phishing_probability = float(result["phishing_probability"])
    legitimate_probability = float(result["legitimate_probability"])
    if result["prediction"] == "phishing":
        prediction = "phishing"
        probability = phishing_probability
    elif result["prediction"] == "legitimate":
        prediction = "safe"
        probability = legitimate_probability
    else:
        logger.error("model returned an unexpected label")
        raise APIError("The analysis could not be completed.", 500, "internal_error")

    signals = build_signals(features, load_importances(settings.resolved_metrics_path))
    level = risk_level(phishing_probability)
    rounded = round(probability, 6)
    facts = build_facts(
        prediction=prediction,
        probability=rounded,
        risk_level=level,
        normalized_url=result["normalized_url"],
        signals=signals,
    )
    try:
        narrative = explain(facts, settings)
    except Exception:
        logger.exception("explanation failed after the classifier finished")
        narrative = fallback_analysis(facts)
    logger.info("prediction=%s risk_level=%s", prediction, level)
    return PredictResponse(
        url=result["normalized_url"],
        prediction=prediction,
        probability=rounded,
        risk_level=level,
        features={name: float(value) for name, value in features.items()},
        signals=signals,
        analysis=Analysis(
            source=narrative.source,
            summary=narrative.summary,
            reasoning=narrative.reasoning,
            risk_factors=narrative.risk_factors,
            recommendations=narrative.recommendations,
        ),
    )


def model_files_present(settings: Settings) -> bool:
    return settings.resolved_model_path.is_file() and settings.resolved_feature_config_path.is_file()


def warmup(settings: Settings) -> bool:
    """Load the forest once. Uses a fixed URL and does not contact that host."""
    if not model_files_present(settings):
        logger.error("model files are missing")
        return False
    try:
        score("https://example.com/", settings)
    except APIError:
        logger.error("model warmup failed")
        return False
    except Exception:
        logger.exception("model warmup failed")
        return False
    return True
