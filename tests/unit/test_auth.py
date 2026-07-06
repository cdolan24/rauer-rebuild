from __future__ import annotations

from src.utils.auth import verify_admin_password


def test_correct_password_matches():
    assert verify_admin_password("secret", "secret") is True


def test_wrong_password_does_not_match():
    assert verify_admin_password("secret", "wrong") is False


def test_no_configured_password_always_fails():
    assert verify_admin_password(None, "secret") is False
    assert verify_admin_password(None, "") is False
