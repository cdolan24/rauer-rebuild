from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from src.utils.rate_limiter import RateLimiter


def get_client_ip(request: Request) -> str:
    """The key to rate-limit admin-password attempts on.

    This app's only supported deployment topology (see
    openspec/specs/deployment/) puts every real request through an Nginx
    reverse proxy on the same host - request.client.host would then always
    be 127.0.0.1 (Nginx's own loopback connection to the backend), which
    collapses every distinct real client onto the same rate-limit bucket.
    That turns the lockout inside-out: one attacker's failed guesses lock
    out every legitimate admin too, and anyone can repeat that indefinitely -
    an unauthenticated denial-of-service against the admin surface, not a
    per-attacker defense. Nginx is configured to forward X-Forwarded-For/
    X-Real-IP (see nginx-udc.conf), so those are trusted ahead of
    the raw ASGI peer address, which remains the fallback for direct/local
    use without a proxy in front.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


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
