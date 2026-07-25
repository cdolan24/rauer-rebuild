from __future__ import annotations

from pathlib import Path

from src.utils.config import get_config_path
from tests.conftest import TEST_ADMIN_PASSWORD


def test_get_backend_config_requires_admin_password(api_client):
    response = api_client.get("/api/admin/backend-config", params={"admin_password": "wrong"})

    assert response.status_code == 401


def test_post_backend_config_requires_admin_password(api_client):
    response = api_client.post(
        "/api/admin/backend-config", json={"admin_password": "wrong", "chat_backend": "hosted_api"}
    )

    assert response.status_code == 401


def test_get_backend_config_defaults_to_ollama(api_client):
    response = api_client.get(
        "/api/admin/backend-config", params={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active_chat_backend"] == "ollama"
    assert data["saved_chat_backend"] == "ollama"
    assert data["hosted_llm"]["api_key_configured"] is False
    # GPU field is always present, informational - value depends on the test host.
    assert "detected" in data["gpu"]


def test_saving_new_backend_does_not_change_active_backend_until_restart(api_client):
    api_client.post(
        "/api/admin/backend-config",
        json={
            "admin_password": TEST_ADMIN_PASSWORD,
            "chat_backend": "hosted_api",
            "hosted_llm_api_key": "sk-test-key",
        },
    )

    response = api_client.get(
        "/api/admin/backend-config", params={"admin_password": TEST_ADMIN_PASSWORD}
    )

    data = response.json()
    assert data["active_chat_backend"] == "ollama"  # unchanged - process hasn't restarted
    assert data["saved_chat_backend"] == "hosted_api"  # but the save landed on disk
    assert data["hosted_llm"]["api_key_configured"] is True


def test_response_never_includes_the_raw_api_key(api_client):
    api_client.post(
        "/api/admin/backend-config",
        json={
            "admin_password": TEST_ADMIN_PASSWORD,
            "chat_backend": "hosted_api",
            "hosted_llm_api_key": "sk-super-secret-value",
        },
    )

    response = api_client.get(
        "/api/admin/backend-config", params={"admin_password": TEST_ADMIN_PASSWORD}
    )

    assert "sk-super-secret-value" not in response.text


def test_omitting_api_key_preserves_the_previously_configured_one(api_client):
    api_client.post(
        "/api/admin/backend-config",
        json={
            "admin_password": TEST_ADMIN_PASSWORD,
            "chat_backend": "hosted_api",
            "hosted_llm_api_key": "sk-keep-me",
        },
    )

    api_client.post(
        "/api/admin/backend-config",
        json={"admin_password": TEST_ADMIN_PASSWORD, "chat_backend": "ollama"},
    )

    config_text = Path(get_config_path()).read_text(encoding="utf-8")
    assert 'api_key: "sk-keep-me"' in config_text


def test_providing_a_new_api_key_replaces_the_old_one(api_client):
    api_client.post(
        "/api/admin/backend-config",
        json={
            "admin_password": TEST_ADMIN_PASSWORD,
            "chat_backend": "hosted_api",
            "hosted_llm_api_key": "sk-old-key",
        },
    )

    api_client.post(
        "/api/admin/backend-config",
        json={
            "admin_password": TEST_ADMIN_PASSWORD,
            "chat_backend": "hosted_api",
            "hosted_llm_api_key": "sk-new-key",
        },
    )

    config_text = Path(get_config_path()).read_text(encoding="utf-8")
    assert 'api_key: "sk-new-key"' in config_text
    assert "sk-old-key" not in config_text


def test_unknown_chat_backend_value_is_rejected(api_client):
    response = api_client.post(
        "/api/admin/backend-config",
        json={"admin_password": TEST_ADMIN_PASSWORD, "chat_backend": "something-else"},
    )

    assert response.status_code == 400
