from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.utils.auth import check_admin_password, verify_admin_password
from src.utils.rate_limiter import RateLimiter


def test_correct_password_matches():
    assert verify_admin_password("secret", "secret") is True


def test_wrong_password_does_not_match():
    assert verify_admin_password("secret", "wrong") is False


def test_no_configured_password_always_fails():
    assert verify_admin_password(None, "secret") is False
    assert verify_admin_password(None, "") is False


def test_check_admin_password_succeeds_with_correct_password():
    limiter = RateLimiter()
    check_admin_password(limiter, "1.2.3.4", "secret", "secret")  # does not raise


def test_check_admin_password_raises_401_on_wrong_password():
    limiter = RateLimiter()
    with pytest.raises(HTTPException) as exc_info:
        check_admin_password(limiter, "1.2.3.4", "secret", "wrong")
    assert exc_info.value.status_code == 401


def test_check_admin_password_locks_out_after_threshold():
    limiter = RateLimiter(max_failures=3, window_seconds=60)
    for _ in range(3):
        with pytest.raises(HTTPException):
            check_admin_password(limiter, "1.2.3.4", "secret", "wrong")

    with pytest.raises(HTTPException) as exc_info:
        check_admin_password(limiter, "1.2.3.4", "secret", "secret")
    assert exc_info.value.status_code == 401
    assert "Too many failed attempts" in exc_info.value.detail
