from __future__ import annotations

import httpx
import pytest

from src.frontend.api_client import ApiAuthError, ApiClient


class _FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self) -> dict:
        return self._json_data


def test_verify_admin_password_succeeds(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: _FakeResponse({"valid": True}))
    client = ApiClient("http://localhost:8000")

    assert client.verify_admin_password("correct") is True


def test_verify_admin_password_raises_with_backend_detail_on_wrong_password(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: _FakeResponse({"detail": "Invalid admin credentials"}, status_code=401),
    )
    client = ApiClient("http://localhost:8000")

    with pytest.raises(ApiAuthError, match="Invalid admin credentials"):
        client.verify_admin_password("wrong")


def test_verify_admin_password_raises_with_lockout_detail(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: _FakeResponse(
            {"detail": "Too many failed attempts - try again later"}, status_code=401
        ),
    )
    client = ApiClient("http://localhost:8000")

    # A locked-out client shouldn't be told "wrong password" - that's a
    # different failure mode with a different fix (wait, don't retry).
    with pytest.raises(ApiAuthError, match="Too many failed attempts"):
        client.verify_admin_password("correct")


def test_run_admin_query_raises_with_backend_detail_on_lockout(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: _FakeResponse(
            {"detail": "Too many failed attempts - try again later"}, status_code=401
        ),
    )
    client = ApiClient("http://localhost:8000")

    with pytest.raises(ApiAuthError, match="Too many failed attempts"):
        client.run_admin_query("SELECT 1", "irrelevant")
