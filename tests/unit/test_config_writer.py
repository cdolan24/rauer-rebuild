from __future__ import annotations

from src.utils.config_writer import update_chat_backend_config

_BASE = """\
# Copy to config.yaml and adjust as needed.

ollama:
  base_url: "http://localhost:11434"
  chat_model: "llama3.2:latest"
  embedding_model: "nomic-embed-text:latest"
  # Local chat generation regularly takes 40-90s+ on modest hardware.
  request_timeout: 450

auth:
  admin_password: "changeme"

chat_backend: "ollama"

# Only read when chat_backend is "hosted_api" above.
# hosted_llm:
#   provider: "anthropic"
#   model: "claude-haiku-4-5"
#   api_key: "changeme"
#   max_tokens: 1024
"""


def test_replaces_existing_chat_backend_value_preserving_everything_else(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_BASE, encoding="utf-8")

    update_chat_backend_config(config_path, chat_backend="hosted_api")

    result = config_path.read_text(encoding="utf-8")
    assert 'chat_backend: "hosted_api"' in result
    # Every unrelated line survives untouched, including comments.
    assert "# Copy to config.yaml and adjust as needed." in result
    assert '  request_timeout: 450' in result
    assert '  admin_password: "changeme"' in result
    # Only one chat_backend line exists.
    assert result.count("chat_backend:") == 1


def test_appends_chat_backend_when_absent(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_BASE.replace('chat_backend: "ollama"\n\n', ""), encoding="utf-8")

    update_chat_backend_config(config_path, chat_backend="hosted_api")

    result = config_path.read_text(encoding="utf-8")
    assert 'chat_backend: "hosted_api"' in result


def test_appends_hosted_llm_block_when_no_live_block_exists(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_BASE, encoding="utf-8")

    update_chat_backend_config(
        config_path, chat_backend="hosted_api", hosted_llm_model="claude-opus-4-8", hosted_llm_api_key="sk-real-key"
    )

    result = config_path.read_text(encoding="utf-8")
    # The commented-out example block is untouched...
    assert "# hosted_llm:" in result
    assert '#   model: "claude-haiku-4-5"' in result
    # ...and a real, uncommented block was appended.
    assert result.count("\nhosted_llm:\n") == 1
    assert 'model: "claude-opus-4-8"' in result
    assert 'api_key: "sk-real-key"' in result
    assert "max_tokens: 1024" in result


def test_replaces_existing_live_hosted_llm_block_entirely(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        _BASE
        + '\nhosted_llm:\n  provider: "anthropic"\n  model: "claude-haiku-4-5"\n'
        + '  api_key: "sk-old-key"\n  max_tokens: 1024\n',
        encoding="utf-8",
    )

    update_chat_backend_config(
        config_path, chat_backend="hosted_api", hosted_llm_model="claude-opus-4-8", hosted_llm_api_key="sk-new-key"
    )

    result = config_path.read_text(encoding="utf-8")
    assert result.count("\nhosted_llm:\n") == 1
    assert 'model: "claude-opus-4-8"' in result
    assert 'api_key: "sk-new-key"' in result
    assert "sk-old-key" not in result


def test_blank_api_key_preserves_existing_key(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        _BASE
        + '\nhosted_llm:\n  provider: "anthropic"\n  model: "claude-haiku-4-5"\n'
        + '  api_key: "sk-keep-me"\n  max_tokens: 1024\n',
        encoding="utf-8",
    )

    update_chat_backend_config(config_path, chat_backend="ollama", hosted_llm_api_key=None)

    result = config_path.read_text(encoding="utf-8")
    assert 'api_key: "sk-keep-me"' in result


def test_blank_api_key_with_no_prior_key_uses_placeholder(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_BASE, encoding="utf-8")

    update_chat_backend_config(config_path, chat_backend="hosted_api")

    result = config_path.read_text(encoding="utf-8")
    assert 'api_key: "changeme"' in result


def test_provided_api_key_replaces_existing(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        _BASE
        + '\nhosted_llm:\n  provider: "anthropic"\n  model: "claude-haiku-4-5"\n'
        + '  api_key: "sk-old-key"\n  max_tokens: 1024\n',
        encoding="utf-8",
    )

    update_chat_backend_config(config_path, chat_backend="hosted_api", hosted_llm_api_key="sk-brand-new")

    result = config_path.read_text(encoding="utf-8")
    assert 'api_key: "sk-brand-new"' in result
    assert "sk-old-key" not in result
