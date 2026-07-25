## 1. GPU detection

- [x] 1.1 Add `src/utils/gpu_detect.py`: `GpuInfo` (`detected: bool`, `name: str | None`) and `detect_gpu() -> GpuInfo` using `shutil.which("nvidia-smi")` + `nvidia-smi --query-gpu=name --format=csv,noheader`; any failure (missing binary, non-zero exit, unexpected output) resolves to `detected=False`, never raises.
- [x] 1.2 Unit tests: no `nvidia-smi` on `PATH` → not detected; present and succeeds → detected with parsed name; present but exits non-zero / unexpected output → not detected (no exception escapes).

## 2. Config file writer

- [x] 2.1 Add `src/utils/config_writer.py`: `update_chat_backend_config(config_path, chat_backend, hosted_llm_model=None, hosted_llm_api_key=None, hosted_llm_max_tokens=None)` - reads the file as text, replaces (or appends) the top-level `chat_backend:` line, and replaces (or appends) the whole top-level `hosted_llm:` block, leaving every other line byte-identical. Read the existing `hosted_llm.api_key` value before deleting the old block, and reuse it when `hosted_llm_api_key` is omitted/blank.
- [x] 2.2 Write atomically (write to a temp file in the same directory, then `os.replace`) so a crash mid-write can't corrupt `config.yaml`.
- [x] 2.3 Unit tests: replaces an existing `chat_backend:` value in place, preserving every comment and every other section byte-for-byte; appends `chat_backend:` when absent; replaces an existing multi-line `hosted_llm:` block entirely; appends `hosted_llm:` when absent; omitted/blank API key preserves the previously-configured one; a provided API key replaces it.

## 3. Admin API endpoints

- [x] 3.1 Add `GET /admin/backend-config` to `src/api/routes/admin.py`, gated by the existing `_check_admin`: returns `{active_chat_backend, saved_chat_backend, hosted_llm: {model, max_tokens, api_key_configured}, gpu: {detected, name}}` - `active_chat_backend` read from `request.app.state.config` (what the running process actually loaded), `saved_chat_backend` read fresh from `config.yaml` on disk (may differ if a save happened without a restart since).
- [x] 3.2 Add `POST /admin/backend-config`, gated the same way: body `{chat_backend, hosted_llm_model?, hosted_llm_api_key?, hosted_llm_max_tokens?}`, calls `update_chat_backend_config`, returns confirmation that a restart is required to take effect.
- [x] 3.3 Integration tests: unauthenticated GET/POST rejected (matches every other admin endpoint's existing test pattern); GET reflects saved vs. active backend correctly when they differ (simulate by writing config after app startup); POST without api_key preserves an existing one; POST with a new api_key replaces it; GET never includes the raw key in its response body under any circumstance.

## 4. Admin page (frontend)

- [x] 4.1 Add `get_backend_config(admin_password)` / `set_backend_config(admin_password, chat_backend, model, api_key, max_tokens)` to `src/frontend/api_client.py`, using the existing `_admin_get`/`_admin_post` helpers.
- [x] 4.2 Add a "Chat Backend" section to the admin page (`src/frontend/app.py`): radio/dropdown for `ollama`/`hosted_api`, model + max_tokens text fields (hosted only), a password-masked API key field (placeholder text like "configured, leave blank to keep" when already set), a GPU status line, a warning banner shown when `ollama` is selected and no GPU is detected, and a Save button whose response explicitly says a restart is required. Load current config into the section on admin unlock (reusing the existing `unlock_admin` reveal flow) rather than requiring a separate manual refresh click.
- [x] 4.3 No new Gradio interaction pattern needed - this isn't an LLM call, so it doesn't need the fire-and-forget-plus-poll treatment the dedupe scan required; a normal synchronous button click is fine (same as every other admin button already in this page).

## 5. Specs and verification

- [x] 5.1 Sync delta specs (`admin-controls` and `llm-chat-backend` both modified) into `openspec/specs/`.
- [x] 5.2 Run the full test suite; confirm no regression.
- [x] 5.3 Manually verify against the real app: save a new `chat_backend` value via the admin page, confirm `config.yaml` on disk has the expected change with every comment/other line untouched (diff against pre-save version), confirm the running process's `/api/health` still reports the old (active) backend until an actual restart, restart via the existing Service Control action, confirm `/api/health` now reports the new backend. Confirm GPU detection reports correctly against this host's real (lack of) GPU.
- [x] 5.4 Archive this change once tasks 1-5.3 are complete and verified.
