"""Application logging. Request logs omit the URL body."""

from __future__ import annotations

import logging

_CONFIGURED = False


def configure_logging(level: str) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        logging.getLogger("intellishield").setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str = "intellishield") -> logging.Logger:
    return logging.getLogger(name)
