from __future__ import annotations

import threading
import time


class RateLimiter:
    """In-memory, per-key fixed-window lockout.

    Single-process only - suitable for this app's single-Uvicorn-worker
    deployment topology. A key (typically a client IP) that racks up too
    many failures within the window is locked out for the remainder of
    that window, checked *before* any password comparison happens.
    """

    def __init__(self, max_failures: int = 5, window_seconds: float = 900.0) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self._window_seconds
        recent = [t for t in self._failures.get(key, []) if t > cutoff]
        self._failures[key] = recent
        return recent

    def is_locked_out(self, key: str) -> bool:
        with self._lock:
            recent = self._prune(key, time.monotonic())
            return len(recent) >= self._max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            recent = self._prune(key, now)
            recent.append(now)
            self._failures[key] = recent

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
