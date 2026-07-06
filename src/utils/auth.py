from __future__ import annotations

import hmac


def verify_admin_password(configured: str | None, provided: str) -> bool:
    """Check a provided admin password against the configured one.

    Returns False if no admin password is configured at all, so a
    forgotten/placeholder config doesn't silently accept anything.
    """
    if configured is None:
        return False
    return hmac.compare_digest(provided, configured)
