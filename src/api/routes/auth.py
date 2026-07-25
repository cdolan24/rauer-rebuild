from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.schemas import AdminAuthRequest, AdminAuthResponse
from src.utils.auth import check_admin_password, get_client_ip

router = APIRouter(tags=["auth"])


@router.post("/auth/verify", response_model=AdminAuthResponse)
def verify(payload: AdminAuthRequest, request: Request) -> AdminAuthResponse:
    config = request.app.state.config
    check_admin_password(
        request.app.state.admin_rate_limiter,
        get_client_ip(request),
        config.admin_password,
        payload.admin_password,
    )
    return AdminAuthResponse(valid=True)
