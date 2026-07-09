#!/usr/bin/env python
"""Minimal, narrowly-scoped local service-control daemon for Buddharauer.

Runs as its own systemd unit (buddharauer-controller.service) with a
sudoers.d rule permitting ONLY `systemctl start/stop/restart` on the app's
two service units (see deploy/sudoers-buddharauer-controller and
deploy/README.md) - nothing else. Binds to 127.0.0.1 only, so it's never
reachable through the reverse proxy, only from the frontend process on the
same host.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from src.utils.auth import check_admin_password
from src.utils.config import get_config_path, load_config
from src.utils.rate_limiter import RateLimiter

_ALLOWED_SERVICES = {"backend": "buddharauer-backend", "frontend": "buddharauer-frontend"}
_ALLOWED_ACTIONS = {"start", "stop", "restart"}

app = FastAPI(title="Buddharauer Controller")
_rate_limiter = RateLimiter()


class ControlRequest(BaseModel):
    admin_password: str


def _require_admin(admin_password: str, client_key: str) -> None:
    config = load_config(get_config_path())
    check_admin_password(_rate_limiter, client_key, config.admin_password, admin_password)


def _resolve_unit(service: str) -> str:
    if service not in _ALLOWED_SERVICES:
        raise HTTPException(status_code=404, detail=f"Unknown service '{service}'")
    return _ALLOWED_SERVICES[service]


@app.post("/control/{service}/{action}")
def control(service: str, action: str, payload: ControlRequest, request: Request) -> dict:
    _require_admin(payload.admin_password, request.client.host)
    unit = _resolve_unit(service)
    if action not in _ALLOWED_ACTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown action '{action}'")

    result = subprocess.run(
        ["sudo", "systemctl", action, unit], capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise HTTPException(
            status_code=500, detail=result.stderr.strip() or "systemctl command failed"
        )
    return {"service": service, "action": action, "status": "ok"}


@app.get("/control/{service}/status")
def status(service: str, admin_password: str, request: Request) -> dict:
    _require_admin(admin_password, request.client.host)
    unit = _resolve_unit(service)

    # Status is read-only and doesn't need sudo - only start/stop/restart do.
    result = subprocess.run(
        ["systemctl", "is-active", unit], capture_output=True, text=True, timeout=10
    )
    return {"service": service, "status": result.stdout.strip()}


if __name__ == "__main__":
    import uvicorn

    config = load_config(get_config_path())
    uvicorn.run(app, host="127.0.0.1", port=config.controller_port)
