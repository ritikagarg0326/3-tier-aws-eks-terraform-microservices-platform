"""Tiny fixed-window in-memory limiter for credential endpoints (per gateway replica)."""
import threading
import time


class RateLimiter:
    def __init__(self, limit: int, window: int = 60):
        self.limit, self.window = limit, window
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            start, count = self._hits.get(key, (now, 0))
            if now - start >= self.window:
                start, count = now, 0
            count += 1
            self._hits[key] = (start, count)
            if len(self._hits) > 10_000:  # bound memory
                self._hits = {k: v for k, v in self._hits.items() if now - v[0] < self.window}
            return count <= self.limit
