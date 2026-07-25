## Why

`dual-target-deployment` made the chat backend (local Ollama vs. hosted Anthropic API) a `config.yaml` setting picked once at deploy time via `deploy/setup_ec2.sh`'s `DEPLOY_PROFILE`. Switching backends today means SSHing in, hand-editing `config.yaml`, and restarting - no way to do it from the admin page, no visibility into whether the host even has a GPU worth using for local chat generation, and no way to enter/rotate the hosted API key without shell access.

## What Changes

- The admin page gains a "Chat Backend" section: shows the currently configured backend, whether the hosted API key is set (never the key itself), and whether a GPU is detected on this host (informational, with a warning if switching to local Ollama chat generation with no GPU detected - matches this project's own documented CPU-only-inference fragility).
- An authenticated admin can submit a new `chat_backend` choice (and, for the hosted option, a model name and/or API key) from the admin page. This writes the change to `config.yaml` - the first place this app writes its own config file, previously read-only - and takes effect after a restart via the *existing* Service Control restart action, not automatically or live.
- New GPU-detection utility (`nvidia-smi`-based, mirroring `deploy/setup_ec2.sh`'s own detection) exposed read-only through the admin page.
- **BREAKING (spec-level, none)** - purely additive: existing config-file-based deployment (`DEPLOY_PROFILE`) keeps working unchanged; this adds a second way to reach the same `chat_backend`/`hosted_llm` settings.

## Capabilities

### Modified Capabilities
- `admin-controls`: add a "Chat Backend Configuration" admin-page capability (view current backend/GPU status, submit a new backend choice/API key, same admin-password gate and rate limiting as every other admin action).
- `llm-chat-backend`: add requirements for how a written-back API key is protected from ever being read back, and that a config-file write itself doesn't apply until an explicit restart (config is only ever read at process startup, per `dual-target-deployment`'s existing design).

## Impact

- `src/utils/gpu_detect.py` (new) - `nvidia-smi`-based GPU detection.
- `src/utils/config_writer.py` (new) - targeted, comment-preserving patch of just the `chat_backend`/`hosted_llm` lines in `config.yaml` (a full YAML round-trip via `yaml.safe_load`/`safe_dump` was measured to strip every comment and reorder keys - unacceptable for a heavily-annotated hand-maintained file).
- `src/api/routes/admin.py` - new `GET`/`POST /admin/backend-config` endpoints.
- `src/frontend/app.py`, `src/frontend/api_client.py` - new admin-page section and API client calls, reusing the existing `_admin_get`/`_admin_post` helpers and the existing Service Control restart action.
- No changes to `src/utils/chat_backend.py` itself (still reads `Config` once at startup, unchanged) or to any deployment script.
