## Context

`config.yaml` has never been written by this app - only ever read, once, via `load_config()` at process startup (`src/api/main.py`'s `lifespan`, and every script's `main()`). It's a hand-maintained file with extensive inline `#` comments explaining non-obvious defaults (timeouts, `keep_alive`, etc.) that a real admin would want preserved even for fields they never touch. A quick empirical check (`yaml.safe_load` + `yaml.safe_dump` round-trip on the real `config.example.yaml`) confirmed a naive round-trip strips every comment and alphabetically reorders every top-level key - unacceptable for this file.

The existing admin page (`src/frontend/app.py`) already has a password-gated Service Control section that restarts the backend via a separate `buddharauer-controller` process (narrowly-scoped `sudoers.d` rule, `deploy/controller.py`) - restarting re-runs `lifespan()` and therefore `load_config()` fresh, with no caching layer to invalidate. The existing dedupe-scan admin action already established the fire-and-forget-plus-poll pattern for anything that blocks on a live LLM call from a single Gradio click (`start_scan`/`check_scan_results` in `app.py`) - notably, restart itself is NOT such an action (a `systemctl restart` subprocess call is fast, not an LLM round-trip), so it doesn't need that treatment.

## Goals / Non-Goals

**Goals:**
- View the currently configured chat backend and hosted-API model from the admin page, without ever exposing a previously-set API key back to the browser.
- View whether this host has a GPU, informationally, with a warning (not a hard block) against choosing local Ollama chat generation with none detected.
- Submit a new `chat_backend` (and, for hosted, model/API key) from the admin page, written to `config.yaml` with every other line/comment byte-identical.
- Require an explicit restart (the existing Service Control action) for the change to take effect - no live in-process backend swap.

**Non-Goals:**
- Live, no-restart backend switching. Rejected per explicit user decision - simpler, matches how every other config change in this app already works (edit + restart), and avoids holding two backend clients live simultaneously.
- Encrypting the API key at rest. It's written to `config.yaml` exactly like `admin_password` already is today - plaintext, admin-password-gated, same trust boundary this project's admin page has always had (see the existing Direct Database Access capability's own accepted risk).
- A general-purpose config editor. Only `chat_backend` and `hosted_llm.*` are exposed - not a raw config.yaml text box.
- Blocking the local-Ollama choice outright when no GPU is detected. Per user decision, this is guidance (a warning), not an enforced restriction - a real GPU-detection false negative (e.g. a supported non-NVIDIA setup, or `nvidia-smi` not yet on `PATH` right after driver install) shouldn't lock an admin out of a valid choice.

## Decisions

### 1. Config file is patched with targeted line/block replacement, not a full YAML round-trip

`src/utils/config_writer.py` reads `config.yaml` as plain text lines and does two independent, minimal edits:
- `chat_backend: "..."` - replace the value on the existing top-level line if present (regex-anchored `^chat_backend:`), else append a new line.
- `hosted_llm:` - if a top-level `hosted_llm:` block exists (the line plus every following more-indented line), delete that whole block and append a freshly-written one with the submitted values; if absent, just append.

Every other line in the file - including all comments, the `ollama:`/`chunking:`/etc. sections, and any `hosted_llm:` fields not touched by this admin action - is left byte-identical. This mirrors the exact technique `deploy/setup_ec2.sh` already uses via `sed` for the same two keys, just in Python instead of shell, applied to an already-existing file instead of a freshly-copied one.

Alternative considered: `ruamel.yaml`, which round-trips comments/ordering by design. Rejected for this change - a new dependency for a two-key patch that a dozen lines of text manipulation already handles correctly, and the technique is already proven (this project's own deploy script does the equivalent thing today).

### 2. Submitting the form without a new API key preserves the existing one; the key is never read back

`GET /admin/backend-config` returns `{chat_backend, hosted_llm: {model, max_tokens, api_key_configured: bool}, gpu: {detected, name}}` - `api_key_configured` is a boolean, never the key itself, matching how `admin_password` is already never echoed back anywhere in this app.

`POST /admin/backend-config` accepts an optional `api_key` field. Semantics: omitted or blank → the write logic in `config_writer.py` re-uses whatever `api_key:` value is already in the existing `hosted_llm:` block (read once before that block is deleted and rewritten) rather than clearing it; a non-blank value replaces it. This lets an admin switch `chat_backend` back and forth between `ollama` and `hosted_api` without having to re-enter the key every time, while still allowing rotation when they do provide a new one.

### 3. GPU detection: `nvidia-smi` subprocess, informational + a warning, not a gate

`src/utils/gpu_detect.py` exposes `detect_gpu() -> GpuInfo` (`detected: bool`, `name: str | None`), implemented as `shutil.which("nvidia-smi")` (mirrors `deploy/setup_ec2.sh`'s own `command -v nvidia-smi` check) followed by `nvidia-smi --query-gpu=name --format=csv,noheader` if present, parsing the first line as the GPU name. Any failure (missing binary, non-zero exit, unexpected output) is treated as "not detected" rather than raised - this is advisory information for an admin decision, not something that should be able to break the admin page if the detection command itself misbehaves.

The admin page shows this next to the backend choice and renders a warning banner (not a disabled control) when the admin selects/has selected `ollama` with `detected: false` - per the Non-Goal above, guidance only.

### 4. Restart stays a manual, separate step using the existing control

Saving the new backend config does not itself trigger a restart. The admin page's existing Service Control "restart backend" button is what applies it - saving just writes the file and shows a "saved - restart the backend for this to take effect" message. This avoids adding a second restart code path and keeps the mental model simple: config changes here work exactly like they would if an admin had SSHed in and hand-edited the file.

## Risks / Trade-offs

- **[Risk]** Two independent admin actions (save config, then restart) means an admin can save and forget to restart, leaving the running process on the old backend with no obvious indicator. → **Mitigation**: the save response text explicitly says a restart is required; the section also always displays the *currently active* backend (read from `request.app.state.config`, the in-memory config the running process actually loaded) separately from the *saved-on-disk* value, so a mismatch after saving is visible rather than silent.
- **[Risk]** Targeted text patching is more fragile than a real YAML parser if a user has hand-edited `config.yaml` into an unusual shape (e.g. `chat_backend` indented under another key by mistake, or a second `hosted_llm:` block). → **Mitigation**: anchor regexes to column 0 (true top-level keys only, matching this file's own consistent style everywhere else); if `chat_backend:` genuinely doesn't exist at top level, append rather than guess - never silently rewrite something that doesn't match the expected shape.
- **[Risk]** `nvidia-smi` presence doesn't guarantee the model that would actually run there is fast enough, only that *a* GPU exists. → **Accepted**: this is explicitly advisory, not a benchmark; a real admin's own judgment about the specific instance/model pairing still applies, same as the deploy script's own driver-presence check today.

## Migration Plan

1. Add `gpu_detect.py` and `config_writer.py` (new, no existing behavior touched).
2. Add the two admin endpoints and wire them behind the existing `_check_admin`/rate-limiter path, identical gating to every other admin endpoint.
3. Add the admin-page section, reusing `_admin_get`/`_admin_post` and the existing restart control - no new Gradio interaction patterns needed (this isn't an LLM call, so no fire-and-forget-plus-poll required).
4. No data migration - `config.yaml`'s existing content is read, minimally patched, and rewritten; nothing about the schema itself changes from `dual-target-deployment`.
5. Rollback: this is purely additive UI/API surface over the existing config fields: reverting the code change leaves `config.yaml` exactly as an admin last saved it (still valid, still loadable) - no cleanup needed.

## Open Questions

None outstanding - the three decisions this needed (switch timing, key storage, GPU detection role) were resolved by explicit user choice before this design was written.
