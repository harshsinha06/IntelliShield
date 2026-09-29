"""FastAPI application."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.database import create_database
from app.routes.health import router as health_router
from app.routes.history import router as history_router
from app.routes.predict import router as predict_router
from app.services.prediction_service import warmup
from app.utils.errors import APIError
from app.utils.logging import configure_logging, get_logger
from app.utils.rate_limit import SlidingWindowLimiter

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(active_settings.log_level)
        app.state.settings = active_settings
        engine, session_factory = create_database(active_settings.resolved_database_url)
        app.state.engine = engine
        app.state.session_factory = session_factory
        app.state.model_available = warmup(active_settings)
        yield
        engine.dispose()

    app = FastAPI(
        title="IntelliShield",
        version="0.3.0",
        summary="Lexical phishing-URL scoring API",
        description=(
            "Scores one URL with the trained Random Forest. "
            "The server does not open or crawl the submitted URL."
        ),
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.model_available = False
    app.state.rate_limiter = SlidingWindowLimiter(
        active_settings.rate_limit_requests,
        active_settings.rate_limit_window_seconds,
    )

    @app.middleware("http")
    async def limit_requests(request: Request, call_next):
        if _is_limited_request(request) and active_settings.rate_limit_enabled:
            client = request.client.host if request.client is not None else "unknown"
            if not request.app.state.rate_limiter.allow(client):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Too many requests. Try again shortly.",
                        }
                    },
                    headers={"Retry-After": str(int(active_settings.rate_limit_window_seconds))},
                )
        return await call_next(request)

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health_router)
    app.include_router(predict_router)
    app.include_router(history_router)

    @app.exception_handler(APIError)
    async def handle_api_error(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": _validation_message(exc)}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, _exc: Exception) -> JSONResponse:
        logger.error("unhandled error type=%s", type(_exc).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "The analysis could not be completed.",
                }
            },
        )

    return app


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "The request could not be validated."
    first = errors[0]
    location = tuple(first.get("loc", ()))
    if "url" in location:
        if first.get("type") == "missing":
            return "URL is required."
        message = str(first.get("msg", "URL is invalid."))
        prefix = "Value error, "
        if message.startswith(prefix):
            message = message[len(prefix) :]
        if message.startswith("Input should"):
            return "URL must be a string."
        return message
    if "analysis_id" in location:
        return "Analysis id must be an integer."
    if "limit" in location:
        return "Limit must be an integer from 1 to 50."
    return "The request could not be validated."


def _is_limited_request(request: Request) -> bool:
    if request.method == "OPTIONS":
        return False
    path = request.url.path
    if request.method == "POST" and path == "/api/v1/predict":
        return True
    return request.method == "GET" and path.startswith("/api/v1/history")


app = create_app()
