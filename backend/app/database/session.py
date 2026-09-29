"""Create the SQLite engine used by the history repository."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


def create_database(url: str) -> tuple[Engine, sessionmaker]:
    """Create tables and return an engine plus a session factory."""
    _prepare_sqlite_path(url)
    kwargs: dict = {}
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url in {"sqlite://", "sqlite:///:memory:"}:
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, connect_args=connect_args, **kwargs)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, factory


def _prepare_sqlite_path(url: str) -> None:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return
    location = url[len(prefix) :]
    if location in {"", ":memory:"}:
        return
    Path(location).expanduser().parent.mkdir(parents=True, exist_ok=True)
