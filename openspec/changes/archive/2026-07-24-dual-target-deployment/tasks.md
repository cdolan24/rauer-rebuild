## 1. Config schema

- [x] 1.1 Add `chat_backend: str` (default `"ollama"`) and a new `HostedLlmConfig` dataclass (`provider`, `model`, `api_key: str | None`, `max_tokens`) to `src/utils/config.py`, loaded from an optional `hosted_llm` section (same optional-section pattern as `rag`/`auth`/`controller` - not a required top-level section, so existing `config.yaml` files need zero changes).
- [x] 1.2 Add `chat_backend` and a commented-out `hosted_llm` block (with placeholder `api_key`, model `claude-haiku-4-5`, `max_tokens: 1024`) to `config.example.yaml`, with a comment on where to get a key and pointing out the key must never be committed - same treatment `admin_password` already gets.
- [x] 1.3 Unit tests for the new config fields: default `chat_backend` is `"ollama"` when unset, `hosted_llm` parses correctly when present, missing `hosted_llm` while `chat_backend: hosted_api` is configured is validated in task 3.4, not here (config loading itself shouldn't require the section - the fail-fast check is a startup concern).

## 2. ChatBackend abstraction

- [x] 2.1 Add `src/utils/chat_backend.py`: `ChatBackend` protocol (`chat`, `chat_stream`, `is_healthy`), `ChatBackendError` exception, `OllamaChatBackend` (thin adapter over the existing `OllamaClient`, binding `chat_model`/`keep_alive` from `OllamaConfig` at construction), `AnthropicChatBackend` (new, using the `anthropic` SDK), and `build_chat_backend(config, ollama_client) -> ChatBackend` factory.
- [x] 2.2 Add the `anthropic` package to `pyproject.toml` dependencies.
- [x] 2.3 `AnthropicChatBackend`: translate a leading `{"role": "system", ...}` message into the SDK's top-level `system` parameter; default `num_predict=None` to the configured `hosted_llm.max_tokens` for the required `max_tokens` param.
- [x] 2.4 `AnthropicChatBackend.chat_stream`: implement via `client.messages.stream(...)` / `.text_stream`, yielding text fragments to match `OllamaChatBackend.chat_stream`'s interface.
- [x] 2.5 Both backends wrap their respective failure modes (`httpx.HTTPError` for Ollama, the `anthropic` SDK's exception types for the hosted backend) in `ChatBackendError`, preserving the cause via `from e`.
- [x] 2.6 `build_chat_backend` raises a clear `ConfigError`-style failure at startup if `chat_backend` is `hosted_api` but `hosted_llm.api_key` is missing/empty - fail fast at startup, not on the first request.
- [x] 2.7 Unit tests: `OllamaChatBackend` delegates correctly to a mocked `OllamaClient`; `AnthropicChatBackend` correctly splits system messages, defaults `max_tokens`, and wraps SDK errors as `ChatBackendError`; `build_chat_backend` selects the right implementation per `chat_backend` value and fails fast per task 2.6.

## 3. Wire call sites to the new backend

- [x] 3.1 `src/api/main.py`: construct the chat backend via `build_chat_backend` at startup, store as `app.state.chat_backend`, alongside the existing `app.state.ollama_client` (unchanged, still used for embeddings and vision).
- [x] 3.2 Update `src/rag/chat_engine.py` (`chat` + `chat_stream`), `src/wiki/summary.py`, `src/pipeline/entity_extractor.py` (both call sites), `src/pipeline/entity_deduper.py`, `src/pipeline/relationship_extractor.py` to take/use a `ChatBackend` instead of calling `ollama_client.chat` directly for chat generation.
- [x] 3.3 Confirm `src/pipeline/image_extractor.py`'s vision-model call site is untouched - it keeps using `ollama_client.chat` directly (vision stays Ollama-only per design's Non-Goals).
- [x] 3.4 Update `GET /api/health` to report `chat_backend.is_healthy()` (labelled with the active backend) separately from `ollama_client.is_healthy()` (embeddings, always checked regardless of chat backend).
- [x] 3.5 Update/add integration tests for the health endpoint covering both chat-backend configurations (healthy/unhealthy for each), and for the affected call sites to confirm they go through the injected backend rather than a hardcoded `OllamaClient`.

## 4. Deployment: cost-optimized AWS profile

- [x] 4.1 Add a `DEPLOY_PROFILE` env var to `deploy/setup_ec2.sh` (`gpu-inhouse` default, or `cpu-hosted-api`); under `cpu-hosted-api`, skip GPU driver installation and the chat-model `ollama pull`, keep the embeddings-model `ollama pull`, and write `chat_backend: hosted_api` (plus a placeholder `hosted_llm.api_key` reminder) into the generated `config.yaml` instead of `chat_backend: ollama`.
- [x] 4.2 Update the script's header comment and completion message to document both profiles, including the "before going live" step of setting a real `hosted_llm.api_key` when using `cpu-hosted-api`.
- [x] 4.3 Update `README.md`'s "Run the app" / deployment section to describe both profiles (in-house/GPU vs AWS cost-optimized/hosted-API) and instance-sizing guidance for each.

## 5. Specs and verification

- [x] 5.1 Sync the delta specs (`llm-chat-backend` new, `deployment`/`rag-chat`/`chat-api` modified) into `openspec/specs/` once implementation matches them.
- [x] 5.2 Run the full test suite; confirm no regression in existing Ollama-backend behavior (default config unchanged).
- [x] 5.3 Manually verify: with `chat_backend: ollama` (default), confirm behavior is unchanged from before this change (RAG chat, wiki summaries, entity extraction all still work against real local Ollama). With `chat_backend: hosted_api` and a real Anthropic API key, confirm a real RAG chat request round-trips through the hosted API and returns a coherent answer, and that `GET /api/health` correctly reports both dependencies.
- [x] 5.4 Archive this change once tasks 1-5.3 are complete and verified.
