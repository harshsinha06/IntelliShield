"""Prediction route. The handler does not fetch or execute the URL."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.repositories.analysis_repository import AnalysisRepository
from app.routes.history import get_repository
from app.schemas.predict import PredictRequest, PredictResponse
from app.services.prediction_service import score
from app.utils.errors import APIError
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(
    body: PredictRequest,
    request: Request,
    repository: AnalysisRepository = Depends(get_repository),
) -> PredictResponse:
    if not request.app.state.model_available:
        raise APIError("The detection model is not loaded.", 503, "model_unavailable")
    result = score(body.url, request.app.state.settings)
    try:
        saved = repository.save(result)
    except Exception as exc:
        logger.error("history save failed type=%s", type(exc).__name__)
    else:
        logger.info("history saved id=%s prediction=%s", saved.id, saved.prediction)
    return result
