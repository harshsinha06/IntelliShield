"""Saved analyses. These routes do not score a URL."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.history import HistoryDetail, HistoryListResponse, detail_from_record, summary_from_record
from app.utils.errors import APIError

router = APIRouter(prefix="/api/v1", tags=["history"])


def get_repository(request: Request) -> Iterator[AnalysisRepository]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    try:
        yield AnalysisRepository(session)
    finally:
        session.close()


@router.get("/history", response_model=HistoryListResponse)
def list_history(
    limit: int = Query(default=20, ge=1, le=50),
    repository: AnalysisRepository = Depends(get_repository),
) -> HistoryListResponse:
    rows = repository.list_recent(limit)
    return HistoryListResponse(items=[summary_from_record(row) for row in rows])


@router.get("/history/{analysis_id}", response_model=HistoryDetail)
def get_history(
    analysis_id: int,
    repository: AnalysisRepository = Depends(get_repository),
) -> HistoryDetail:
    record = repository.get(analysis_id)
    if record is None:
        raise APIError("That analysis was not found.", 404, "not_found")
    return detail_from_record(record)
