from __future__ import annotations

import time

from src.utils.rate_limiter import RateLimiter


def test_not_locked_out_before_threshold():
    limiter = RateLimiter(max_failures=3, window_seconds=60)
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.is_locked_out("1.2.3.4") is False


def test_locked_out_at_threshold():
    limiter = RateLimiter(max_failures=3, window_seconds=60)
    for _ in range(3):
        limiter.record_failure("1.2.3.4")
    assert limiter.is_locked_out("1.2.3.4") is True


def test_lockout_is_per_key():
    limiter = RateLimiter(max_failures=3, window_seconds=60)
    for _ in range(3):
        limiter.record_failure("1.2.3.4")
    assert limiter.is_locked_out("5.6.7.8") is False


def test_lockout_expires_after_window():
    limiter = RateLimiter(max_failures=3, window_seconds=0.05)
    for _ in range(3):
        limiter.record_failure("1.2.3.4")
    assert limiter.is_locked_out("1.2.3.4") is True
    time.sleep(0.1)
    assert limiter.is_locked_out("1.2.3.4") is False


def test_success_clears_recorded_failures():
    limiter = RateLimiter(max_failures=3, window_seconds=60)
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    limiter.record_success("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.is_locked_out("1.2.3.4") is False


def test_success_alone_does_not_cause_lockout():
    limiter = RateLimiter(max_failures=3, window_seconds=60)
    for _ in range(10):
        limiter.record_success("1.2.3.4")
    assert limiter.is_locked_out("1.2.3.4") is False
