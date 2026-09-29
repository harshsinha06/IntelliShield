"""History list and detail responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.models.analysis import AnalysisRecord
from app.schemas.predict import Analysis, PredictResponse, Signal


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class HistorySummary(BaseModel):
    id: int
    created_at: datetime
    url: str
    prediction: Literal["safe", "phishing"]
    probability: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]


class HistoryListResponse(BaseModel):
    items: list[HistorySummary]


class HistoryDetail(PredictResponse):
    id: int
    created_at: datetime


def summary_from_record(record: AnalysisRecord) -> HistorySummary:
    return HistorySummary(
        id=record.id,
        created_at=_as_utc(record.created_at),
        url=record.url,
        prediction=record.prediction,
        probability=float(record.probability),
        risk_level=record.risk_level,
    )


def detail_from_record(record: AnalysisRecord) -> HistoryDetail:
    return HistoryDetail(
        id=record.id,
        created_at=_as_utc(record.created_at),
        url=record.url,
        prediction=record.prediction,
        probability=float(record.probability),
        risk_level=record.risk_level,
        features={name: float(value) for name, value in dict(record.features).items()},
        signals=[Signal.model_validate(item) for item in list(record.signals)],
        analysis=Analysis.model_validate(record.analysis),
    )
