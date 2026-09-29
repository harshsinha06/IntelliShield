"""Read and write saved analyses. Callers pass an open session."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRecord
from app.schemas.predict import PredictResponse
from app.services.llm_service import redact_url


class AnalysisRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, result: PredictResponse) -> AnalysisRecord:
        """Store the classifier result. Query values and userinfo are not kept."""
        record = AnalysisRecord(
            created_at=datetime.now(timezone.utc),
            url=redact_url(result.url),
            prediction=result.prediction,
            probability=result.probability,
            risk_level=result.risk_level,
            features=dict(result.features),
            signals=[signal.model_dump() for signal in result.signals],
            analysis=result.analysis.model_dump(),
        )
        self._session.add(record)
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._session.refresh(record)
        return record

    def list_recent(self, limit: int) -> list[AnalysisRecord]:
        statement = (
            select(AnalysisRecord)
            .order_by(AnalysisRecord.created_at.desc(), AnalysisRecord.id.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement))

    def get(self, analysis_id: int) -> AnalysisRecord | None:
        return self._session.get(AnalysisRecord, analysis_id)
