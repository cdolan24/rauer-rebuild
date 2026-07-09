from __future__ import annotations

import hmac

from fastapi import HTTPException

from src.utils.rate_limiter import RateLimiter


def verify_admin_password(configured: str | None, provided: str) -> bool:
    """Check a provided admin password against the configured one.

    Returns False if no admin password is configured at all, so a
    forgotten/placeholder config doesn't silently accept anything.
    """
    if configured is None:
        return False
    return hmac.compare_digest(provided, configured)


def check_admin_password(
    rate_limiter: RateLimiter, client_key: str, configured: str | None, provided: str
) -> None:
    """Raise HTTPException(401) if the client is locked out or the password is
    wrong; otherwise return normally. Lockout is checked *before* comparing the
    password, so a locked-out client is rejected even with the right password."""
    if rate_limiter.is_locked_out(client_key):
        raise HTTPException(status_code=401, detail="Too many failed attempts - try again later")
    if not verify_admin_password(configured, provided):
        rate_limiter.record_failure(client_key)
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    rate_limiter.record_success(client_key)
