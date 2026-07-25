## Why

The only deployment path this app has (`deploy/setup_ec2.sh`, `openspec/specs/deployment/`) assumes a GPU-backed EC2 instance running Ollama for both chat generation and embeddings - chosen specifically because CPU-only Ollama chat generation was measured as too slow (~27s prompt eval) to ship without a GPU. A live cost comparison this session found that keeping a `g4dn.xlarge` GPU instance running to solve that problem costs roughly 20-200x more (~$384/month at 24/7 on-demand) than this app's actual usage pattern would cost against a hosted LLM API (~$2-20/month for a personal, low-traffic RAG chatbot). There is also a real need to deploy this on a machine already owned in-house, where GPU cost isn't a concern and the existing all-local architecture is fine as-is.

This change adds a second, cost-optimized deployment profile for AWS that drops the GPU requirement by moving chat generation to a hosted LLM API, while keeping embeddings on local Ollama (embeddings were never the slow/fragile part). The existing in-house/GPU profile is kept, unchanged, as the option for hardware already owned.

## What Changes

- Add a chat-generation backend abstraction with two implementations - the existing Ollama-backed chat, and a new hosted-API-backed chat (Anthropic Claude Haiku) - selected via `config.yaml`. Every existing call site that generates chat text (RAG answers, wiki entity summaries, entity/relationship extraction) goes through this abstraction instead of calling `OllamaClient.chat` directly.
- Embeddings (`nomic-embed-text`) and the optional vision model stay on local Ollama in every deployment profile - **not** part of this change's abstraction.
- **BREAKING (spec-level):** `rag-chat`'s "Local-Only Model Execution" requirement currently guarantees no cloud LLM calls happen at runtime, unconditionally. This becomes conditional on the configured chat backend: local-only is still guaranteed when `chat_backend: ollama` (the in-house profile's default), but explicitly not guaranteed when `chat_backend: hosted_api` is configured.
- Add a second deployment target: a non-GPU, cost-optimized AWS profile (a small CPU-only instance running Ollama for embeddings only, chat routed to the hosted API, secrets via an env-provided API key that is never committed). This keeps the existing systemd + Nginx architecture (`deploy/setup_ec2.sh`) rather than introducing containers - the prior deployment change explicitly rejected containerizing specifically because Fargate can't attach a GPU; that GPU constraint no longer applies to this profile, but the simplicity argument (systemd services, minimal divergence from local dev) still does, so this change keeps that architecture and just makes the GPU/driver install and Ollama chat-model pull conditional on which profile is being set up.
- The existing GPU/in-house profile (`deploy/setup_ec2.sh` as it works today) is kept as-is for deployment onto owned hardware.
- Update `README.md`'s "Run the app" section and `openspec/specs/deployment/` to document both profiles.
- Health check (`GET /api/health`) reports the configured chat backend's reachability, not just Ollama's, since Ollama may no longer be in the chat path.

## Capabilities

### New Capabilities
- `llm-chat-backend`: Config-selectable chat-generation backend (local Ollama vs hosted API), used by every part of the app that generates chat text.

### Modified Capabilities
- `deployment`: add the second, non-GPU/hosted-API AWS profile alongside the existing GPU/in-house profile; setup script and docs cover both.
- `rag-chat`: "Local-Only Model Execution" requirement becomes conditional on the configured chat backend instead of an unconditional guarantee.
- `chat-api`: health endpoint reports the configured chat backend's status, not hardcoded Ollama-only status.

## Impact

- `src/utils/ollama_client.py` (chat method used by RAG chat, wiki summaries, entity extraction/relationships) - call sites move behind the new abstraction.
- `config.yaml` / `config.example.yaml` - new `chat_backend` setting and, when hosted, an API-key setting (env-sourced, not committed).
- `deploy/setup_ec2.sh`, `deploy/nginx-buddharauer.conf`, systemd units - conditional GPU/driver/model-pull steps per profile.
- `README.md`, `openspec/specs/deployment/spec.md`, `openspec/specs/rag-chat/spec.md`, `openspec/specs/chat-api/spec.md`.
- No changes to embeddings, vision-model, vector store, or entity-storage code paths.
