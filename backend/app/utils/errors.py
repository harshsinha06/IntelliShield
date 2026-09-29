"""Errors returned to API clients. Messages do not include the submitted URL."""

from __future__ import annotations


class APIError(Exception):
    def __init__(self, message: str, status_code: int, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
