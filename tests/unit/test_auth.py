from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.utils.auth import check_admin_password, get_client_ip, verify_admin_password
from src.utils.rate_limiter import RateLimiter


def _make_request(headers: dict[str, str] | None = None, client: tuple[str, int] | None = ("127.0.0.1", 12345)) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": client,
    }
    return Request(scope)


def test_get_client_ip_falls_back_to_asgi_peer_when_no_proxy_headers():
    assert get_client_ip(_make_request()) == "127.0.0.1"


def test_get_client_ip_prefers_x_forwarded_for():
    request = _make_request(headers={"X-Forwarded-For": "203.0.113.5"})
    assert get_client_ip(request) == "203.0.113.5"


def test_get_client_ip_takes_the_first_hop_in_x_forwarded_for():
    """The leftmost entry is the original client; later entries are
    intermediate proxies (e.g. Nginx's own address appended to the chain)."""
    request = _make_request(headers={"X-Forwarded-For": "203.0.113.5, 127.0.0.1"})
    assert get_client_ip(request) == "203.0.113.5"


def test_get_client_ip_falls_back_to_x_real_ip():
    request = _make_request(headers={"X-Real-IP": "203.0.113.9"})
    assert get_client_ip(request) == "203.0.113.9"


def test_get_client_ip_prefers_x_forwarded_for_over_x_real_ip():
    request = _make_request(headers={"X-Forwarded-For": "203.0.113.5", "X-Real-IP": "203.0.113.9"})
    assert get_client_ip(request) == "203.0.113.5"


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
