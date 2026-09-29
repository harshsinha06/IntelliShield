"""Health route."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", model_loaded=bool(request.app.state.model_available))
