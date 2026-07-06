from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import AdminAuthRequest, AdminAuthResponse
from src.utils.auth import verify_admin_password

router = APIRouter(tags=["auth"])


@router.post("/auth/verify", response_model=AdminAuthResponse)
def verify(payload: AdminAuthRequest, request: Request) -> AdminAuthResponse:
    config = request.app.state.config
    if not verify_admin_password(config.admin_password, payload.admin_password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return AdminAuthResponse(valid=True)
