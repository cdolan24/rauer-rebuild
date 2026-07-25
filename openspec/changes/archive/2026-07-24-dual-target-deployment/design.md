## Context

Every chat-generation call in this codebase goes through `OllamaClient.chat`/`chat_stream` (`src/utils/ollama_client.py`), constructed once in `src/api/main.py` and threaded through `app.state.ollama_client`. Six call sites use it for chat generation: `src/rag/chat_engine.py` (RAG answers, `chat` + `chat_stream`), `src/wiki/summary.py` (entity summaries), `src/pipeline/entity_extractor.py` (x2), `src/pipeline/entity_deduper.py`, `src/pipeline/relationship_extractor.py`. A seventh call site, `src/pipeline/image_extractor.py`, also calls `ollama_client.chat` but for the vision model - out of scope here, stays hard-wired to Ollama (see Non-Goals). Embeddings (`OllamaClient.embed`) are a separate method entirely and are untouched.

`openspec/specs/rag-chat/spec.md` currently states an unconditional requirement, "Local-Only Model Execution": no cloud LLM calls at runtime, ever. That requirement was true and correct for the single deployment target that existed when it was written. This change deliberately makes it conditional: still an absolute guarantee for the in-house/GPU profile (`chat_backend: ollama`), explicitly not guaranteed for the new AWS profile (`chat_backend: hosted_api`).

The existing deployment design (`openspec/changes/archive/2026-07-08-deployment-and-admin-controls/design.md`) explicitly rejected containers/ECS because Fargate cannot attach a GPU and the whole point of that deployment was GPU-backed inference. That constraint doesn't apply to the new AWS profile (no GPU needed once chat isn't running through Ollama) - but the simplicity argument for staying on plain systemd + Nginx (matches local dev, no registry/task-definition/networking overhead for a single-service app) still holds regardless of GPU. This change keeps that architecture for both profiles rather than introducing containers now.

Secrets already have an established pattern in this codebase: `admin_password` lives directly in the gitignored `config.yaml` (see `src/utils/config.py`), not a separate `.env`/secrets-manager mechanism. The new hosted-API key follows the same pattern rather than introducing a new one.

## Goals / Non-Goals

**Goals:**
- A `ChatBackend` abstraction with two implementations - Ollama (existing behavior, default) and a hosted API (new) - selected by one `config.yaml` setting, used by every chat-generation call site.
- A cost-optimized AWS deployment profile: no GPU, no local chat model, embeddings-only Ollama on a small CPU instance, chat routed to the hosted backend.
- The existing GPU/in-house profile keeps working exactly as it does today, unchanged, as the option for hardware already owned.
- `rag-chat`'s local-only guarantee becomes conditional on the configured backend, documented as such rather than silently broken.

**Non-Goals:**
- Containerizing the app. Neither deployment profile needs it (see Context) - this change extends `deploy/setup_ec2.sh` and its systemd units, it doesn't replace them.
- A hosted embeddings provider. Embeddings and the optional vision model stay on local Ollama in every profile - this change only touches the chat-generation path.
- Actually provisioning AWS infrastructure or spending real money. This produces reviewable artifacts (a setup-script profile, config, docs) the user applies against their own account, same posture as the existing GPU deployment change - no AWS credentials exist in this environment.
- Multi-provider hosted API support (OpenAI, etc.) - one concrete hosted implementation (Anthropic) is enough to prove the abstraction; adding more providers later only means adding another `ChatBackend` implementation, not touching the interface or call sites again.
- Supporting a mix of backends *within* one running instance (e.g. hosted for RAG chat but Ollama for entity extraction) - one backend setting applies to the whole process. Revisit only if a real need for per-call-site backend selection shows up.

## Decisions

### 1. `ChatBackend` protocol, model bound at construction, not passed per-call

```python
class ChatBackend(Protocol):
    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.7, num_predict: int | None = None) -> str: ...
    def chat_stream(self, messages: list[dict[str, str]], *, temperature: float = 0.7, num_predict: int | None = None) -> Iterator[str]: ...
    def is_healthy(self) -> tuple[bool, str]: ...
```

Every current call site passes its own `chat_model` string pulled from `config.ollama.chat_model` on every call - that made sense with one backend, but the two backends here have model identifiers from entirely different namespaces (`"llama3.2:latest"` vs `"claude-haiku-4-5"`), so the model belongs to the backend instance, fixed at construction from whichever config section matches the active backend, not passed in by each call site. `keep_alive` (Ollama-specific, meaningless to a hosted API) drops out of the shared interface entirely and becomes an implementation detail `OllamaChatBackend` reads from its own config.

`num_predict` stays optional in the shared interface (matches today's Ollama call sites, several of which omit it) but `AnthropicChatBackend` translates `None` to a configured default (Anthropic's Messages API requires `max_tokens`, unlike Ollama where omitting `num_predict` just means "no cap") - default sourced from a new `hosted_llm.max_tokens` config value (1024) so this isn't a silent magic number.

Alternative considered: keep passing `model` per call, add a `backend` dimension as a second parameter alongside it. Rejected - every current call site already hardcodes which conceptual model it wants (the main chat model, always); the only new axis is *which service* serves that concept, which is exactly what swapping the bound `ChatBackend` instance covers with zero call-site changes beyond the constructor wiring in `src/api/main.py`.

### 2. `OllamaChatBackend` wraps the existing `OllamaClient` unchanged; `AnthropicChatBackend` is new, using Anthropic's official Python SDK

`OllamaClient` itself doesn't change - `OllamaChatBackend` is a thin adapter binding `chat_model`/`keep_alive` from `config.ollama` and delegating straight through. `AnthropicChatBackend` uses the `anthropic` package (new dependency, added to `pyproject.toml`) rather than hand-rolling HTTP/SSE parsing - streaming in particular (`client.messages.stream(...).text_stream`) is exactly what `chat_stream` needs and isn't worth reimplementing.

Message translation: Ollama's message list allows a `"system"` role inline; Anthropic's Messages API takes `system` as a separate top-level string, not a message-list entry. `AnthropicChatBackend.chat`/`chat_stream` split any leading `{"role": "system", ...}` messages out of the list and join them into the `system` parameter before calling the SDK.

Model id: `claude-haiku-4-5` (current cheapest/fastest Claude model, the one this session's cost comparison was based on), configurable via `hosted_llm.model` so it isn't hardcoded past this change's default.

API key: `hosted_llm.api_key`, read from `config.yaml` directly (gitignored already), same pattern as `admin_password` - not a new `.env`/secrets-manager mechanism. `config.example.yaml` documents the field with a placeholder and a comment pointing at where to get a key; the real value never gets committed, exactly like `admin_password` today.

### 3. Factory function picks the backend once at startup; `is_healthy` becomes backend-reported instead of Ollama-hardcoded

`build_chat_backend(config) -> ChatBackend` in a new `src/utils/chat_backend.py`, called once in `src/api/main.py`, stored as `app.state.chat_backend`. Every call site that today reads `request.app.state.ollama_client` for chat generation switches to `request.app.state.chat_backend`; sites that only need embeddings (document ingestion) or the vision model (`image_extractor.py`) keep using `request.app.state.ollama_client` directly, unaffected.

`GET /api/health` (`chat-api` spec) currently reports Ollama connectivity specifically. It changes to report `chat_backend.is_healthy()` (labelled with which backend is active) for the chat-generation dependency, plus a separate, unconditional check of `ollama_client.is_healthy()` for the embeddings dependency (which is never optional in either profile) - so health reporting stays accurate about what's actually in the request path in each profile, rather than silently describing Ollama when a hosted-API profile no longer depends on it for chat.

### 4. Deployment: one setup script, a `DEPLOY_PROFILE` switch, not two forked scripts

`deploy/setup_ec2.sh` gains a `DEPLOY_PROFILE` env var (`gpu-inhouse` default, or `cpu-hosted-api`) rather than duplicating the whole script. GPU driver install and `ollama pull llama3.2:latest` are skipped under `cpu-hosted-api`; `ollama pull nomic-embed-text:latest` (embeddings) always runs in both profiles. The generated `config.yaml` sets `chat_backend` to match the profile. Instance-type guidance moves from one hardcoded assumption ("tested target: g4dn.xlarge") to profile-specific guidance in the script's header comment and `README.md` (e.g. a small `t3.small`/`t3.medium` for `cpu-hosted-api`, since it's no longer running any chat-generation model locally).

Alternative considered: a second script (`setup_ec2_cpu.sh`). Rejected - the two profiles share the vast majority of steps (users, venv, Nginx, systemd units, backup timer); a single switch is less to keep in sync than two near-duplicate scripts, and matches this codebase's general preference for config-driven branching over duplicated code paths.

### 5. `rag-chat`'s local-only requirement becomes conditional, stated explicitly rather than silently narrowed

The requirement text changes from an unconditional guarantee to: local-only when `chat_backend: ollama`, not guaranteed when `chat_backend: hosted_api` - both stated as scenarios in the same requirement, so the spec still makes an affirmative claim about behavior in both configurations rather than just deleting the guarantee.

## Risks / Trade-offs

- **[Risk]** A hosted-API profile sends chat prompts (which may include story/document content and prior conversation turns) to a third-party API - a real change from "everything stays on this machine." → **Mitigation**: this is exactly what `chat_backend: hosted_api` is for and is opt-in per deployment profile; the in-house/GPU profile's default stays `ollama` and keeps the unconditional local-only guarantee unchanged. Documented plainly in the updated `rag-chat` spec and `README.md`, not left implicit.
- **[Risk]** `AnthropicChatBackend`'s error handling needs to distinguish transient/retryable failures (rate limits, timeouts) from configuration failures (bad API key) - getting this wrong could either mask a real outage as healthy or spam retries against a bad key. → **Mitigation**: mirror `OllamaError`'s existing shape (a single exception type callers already know how to catch) - `ChatBackendError` raised for both backends, with the underlying cause preserved via `from e`; no new retry logic is added by this change beyond what individual call sites already do for `OllamaError` today.
- **[Risk]** Introducing a new dependency (`anthropic` SDK) on a project that otherwise has almost no external LLM-facing dependencies. → **Accepted**: the alternative (hand-rolled SSE streaming parser) is more code to maintain for a well-solved problem; the SDK is Anthropic's own official client.
- **[Risk]** `max_tokens` defaulting (1024) could truncate a hosted-API answer at a different point than the Ollama profile's `num_predict: 512` would have, giving inconsistent answer length between profiles. → **Accepted**: profiles are expected to diverge somewhat (that's the point of having two); 1024 is a starting default in `config.example.yaml`, easily tuned per deployment, not a hidden constant.

## Migration Plan

1. Add `ChatBackend`/`OllamaChatBackend`/`AnthropicChatBackend`/`build_chat_backend` (new code, nothing removed yet) plus the `chat_backend`/`hosted_llm` config schema (new, optional-with-default-`ollama` so existing `config.yaml` files on the in-house profile need zero changes to keep working exactly as today).
2. Switch call sites from `app.state.ollama_client` to `app.state.chat_backend` for chat generation only; `image_extractor.py` and embedding call sites are untouched.
3. Update `GET /api/health`, `deploy/setup_ec2.sh` (profile switch), `README.md`, and the delta specs.
4. No data migration - this is a code/config/deploy-script change with no schema or stored-data impact.
5. Rollback: setting `chat_backend: ollama` (or omitting it, since that's the default) fully restores today's behavior with no code changes needed; reverting the code change itself is a plain revert with no migration to undo, since nothing existing was altered in place.

## Open Questions

- Whether to add retry/backoff specifically for hosted-API rate limits beyond what's already done for `OllamaError` - left as a follow-up once this is actually exercised against real traffic; not resolved here.
- Exact small-instance type for the `cpu-hosted-api` AWS profile (`t3.small` vs `t3.medium`) - left for the user to size against real embedding-throughput needs when they actually provision it; the setup script documents the recommendation but doesn't hardcode a launch template.
