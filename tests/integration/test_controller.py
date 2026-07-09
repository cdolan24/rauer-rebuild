from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

import deploy.controller as controller_module
from tests.conftest import TEST_ADMIN_PASSWORD, write_test_config


@pytest.fixture
def controller_client(tmp_path, monkeypatch):
    config_path = write_test_config(tmp_path)
    monkeypatch.setenv("BUDDHARAUER_CONFIG", config_path)
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
