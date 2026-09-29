"""Settings loaded from the environment. API keys are never written to logs."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = REPO_ROOT / "ml" / "models" / "phishing_rf.joblib"
DEFAULT_FEATURE_CONFIG_PATH = REPO_ROOT / "ml" / "models" / "feature_config.json"
DEFAULT_METRICS_PATH = REPO_ROOT / "ml" / "models" / "metrics.json"
DEFAULT_DATABASE_PATH = REPO_ROOT / "backend" / "data" / "intellishield.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    model_path: str = ""
    feature_config_path: str = ""
    metrics_path: str = ""
    openai_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    openai_base_url: str = ""
    openai_model: str = ""
    llm_timeout_seconds: float = 20.0
    database_url: str = ""
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 60
    rate_limit_window_seconds: float = 60.0

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("llm_timeout_seconds")
    @classmethod
    def require_positive_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("LLM_TIMEOUT_SECONDS must be positive.")
        return value

    @field_validator("cors_origins")
    @classmethod
    def reject_wildcard_origin(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        if any(item == "*" for item in origins):
            raise ValueError("CORS_ORIGINS must list explicit origins. A wildcard is not allowed.")
        return value

    @field_validator("rate_limit_requests")
    @classmethod
    def require_positive_rate_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("RATE_LIMIT_REQUESTS must be at least 1.")
        return value

    @field_validator("rate_limit_window_seconds")
    @classmethod
    def require_positive_window(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("RATE_LIMIT_WINDOW_SECONDS must be positive.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def resolved_model_path(self) -> Path:
        return Path(self.model_path).expanduser() if self.model_path else DEFAULT_MODEL_PATH

    @property
    def resolved_feature_config_path(self) -> Path:
        if self.feature_config_path:
            return Path(self.feature_config_path).expanduser()
        return DEFAULT_FEATURE_CONFIG_PATH

    @property
    def resolved_metrics_path(self) -> Path:
        if self.metrics_path:
            return Path(self.metrics_path).expanduser()
        return DEFAULT_METRICS_PATH

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{DEFAULT_DATABASE_PATH}"
