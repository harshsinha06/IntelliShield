"""One saved classifier result.

The URL column is the normalized URL after userinfo and query values are
removed. The row does not store the client address, request headers, or any
API key.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    url: Mapped[str] = mapped_column(String)
    prediction: Mapped[str] = mapped_column(String(16))
    probability: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    features: Mapped[dict] = mapped_column(JSON)
    signals: Mapped[list] = mapped_column(JSON)
    analysis: Mapped[dict] = mapped_column(JSON)
