"""Request and response models for URL scoring."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.ml import MAX_URL_LENGTH


class PredictRequest(BaseModel):
    url: str = Field(examples=["https://example.com/docs"])

    @field_validator("url")
    @classmethod
    def require_url_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("URL is required.")
        if len(stripped) > MAX_URL_LENGTH:
            raise ValueError(f"URL must be at most {MAX_URL_LENGTH} characters.")
        return stripped


class Signal(BaseModel):
    feature: str
    value: float
    importance: float
    summary: str


class Analysis(BaseModel):
    """Explanation of the classifier result. It is not a second verdict."""

    source: Literal["llm", "fallback"]
    summary: str
    reasoning: list[str]
    risk_factors: list[str]
    recommendations: list[str]


class PredictResponse(BaseModel):
    url: str
    prediction: Literal["safe", "phishing"]
    probability: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]
    features: dict[str, float]
    signals: list[Signal]
    analysis: Analysis


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
