"""In-memory request limit for the local API.

The key is the direct client address. X-Forwarded-For is not trusted, because
a caller can set that header. A reverse proxy in front of this process would
need its own limit.
"""

from __future__ import annotations

import threading
import time


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        with self._lock:
            recent = [stamp for stamp in self._hits.get(key, []) if moment - stamp < self.window_seconds]
            if len(recent) >= self.limit:
                self._hits[key] = recent
                return False
            recent.append(moment)
            self._hits[key] = recent
            return True
