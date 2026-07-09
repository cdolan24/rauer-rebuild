from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

import deploy.controller as controller_module
from src.utils.rate_limiter import RateLimiter
from tests.conftest import TEST_ADMIN_PASSWORD, write_test_config


@pytest.fixture
def controller_client(tmp_path, monkeypatch):
    config_path = write_test_config(tmp_path)
    monkeypatch.setenv("BUDDHARAUER_CONFIG", config_path)
    # controller_module.app and its rate limiter are process-wide singletons
    # (the controller is meant to run as one long-lived systemd process) -
    # give each test a fresh limiter so failures in one test don't lock out
    # a later test using the same TestClient host.
    monkeypatch.setattr(controller_module, "_rate_limiter", RateLimiter())
    return TestClient(controller_module.app)


class _FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_control_restarts_service_with_correct_password(controller_client, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = controller_client.post(
        "/control/backend/restart", json={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json() == {"service": "backend", "action": "restart", "status": "ok"}
    assert calls == [["sudo", "systemctl", "restart", "buddharauer-backend"]]


def test_control_rejects_wrong_password_without_running_systemctl(controller_client, monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: calls.append(cmd))

    response = controller_client.post(
        "/control/backend/restart", json={"admin_password": "wrong"}
    )

    assert response.status_code == 401
    assert calls == []  # never touched systemctl


def test_control_rejects_unknown_service(controller_client, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _FakeCompletedProcess())

    response = controller_client.post(
        "/control/nonexistent/restart", json={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 404


def test_control_rejects_unknown_action(controller_client, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _FakeCompletedProcess())

    response = controller_client.post(
        "/control/backend/destroy", json={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 404


def test_control_returns_500_when_systemctl_fails(controller_client, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **kw: _FakeCompletedProcess(returncode=1, stderr="unit not found")
    )

    response = controller_client.post(
        "/control/frontend/stop", json={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 500
    assert "unit not found" in response.json()["detail"]


def test_status_returns_systemctl_output(controller_client, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _FakeCompletedProcess(stdout="active\n"))

    response = controller_client.get(
        "/control/backend/status", params={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json() == {"service": "backend", "status": "active"}


def test_status_rejects_wrong_password(controller_client, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _FakeCompletedProcess(stdout="active"))

    response = controller_client.get(
        "/control/backend/status", params={"admin_password": "wrong"}
    )

    assert response.status_code == 401


def test_repeated_wrong_passwords_lock_out_even_the_correct_password(controller_client, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _FakeCompletedProcess(stdout="active"))

    for _ in range(5):
        controller_client.get("/control/backend/status", params={"admin_password": "wrong"})

    response = controller_client.get(
        "/control/backend/status", params={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 401
    assert "Too many failed attempts" in response.json()["detail"]
