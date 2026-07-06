# Session Log: 2026-07-06 - Backend->Ollama Timeout Fix

**Branch:** `rebuild-mvp`
**OpenSpec changes covered:** none (bug fix, no active change needed)

## Summary

New session started with no pending OpenSpec tasks and the product already running from the prior session (backend/frontend processes survived the session boundary). User reported a `500 Internal Server Error` when using the deployed app; this session debugged and fixed it.

## Root cause

`src/api/main.py` constructed `OllamaClient(config.ollama.base_url)` with no explicit timeout, so it used the client's default (60s). Real `llama3.2` chat generation regularly takes 40-90s+. Once the backend's own call to Ollama exceeded 60s, `OllamaClient.chat()` raised `OllamaError`, which wasn't caught anywhere specific and fell through to the generic `Exception` handler in `main.py`, surfacing as an opaque `500`.

This is the same class of bug fixed on the *frontend* side in the previous session (`frontend.request_timeout` raised from 60s to 180s) - but that fix only addressed the frontend->backend leg. The backend->Ollama leg still had the same 60s ceiling, so the underlying problem was still there, just moved one hop over. Confirmed via `backend.log`: `src.utils.ollama_client.OllamaError: Failed to reach Ollama chat endpoint: timed out`.

## Fix

- Added `ollama.request_timeout` (default 180s) to config, documented in `config.example.yaml` with a note that it must be >= `frontend.request_timeout` or the backend gives up before the frontend does.
- `src/api/main.py` and `scripts/process_documents.py` now pass this timeout when constructing `OllamaClient`.
- `chat.py` and `search.py` routes now catch `OllamaError` specifically and return `503` with a clear "Local LLM service unavailable" message, instead of relying on the generic 500 handler for an expected/recoverable failure mode.
- Added tests: config default/override for `ollama.request_timeout`, and 503 responses from `/api/chat` and `/api/search` when Ollama is unavailable (`unhealthy_api_client` fixture).
- Fixed conftest.py's monkeypatched `OllamaClient` lambdas, which didn't accept the new `timeout` kwarg (caught immediately by the test suite).

## Verification

- 62/62 tests passing.
- Direct `curl` against the real backend: 57.9s response, `200 OK` (previously would have hit the 60s ceiling).
- Playwright against the real frontend: full chat round-trip at ~60s, no error.

## State at end of session

- Commit `d1e6dc2` pushed to `rebuild-mvp`.
- Backend restarted with the fix; frontend left running (unaffected by this change, no restart needed).
- Both PDFs still indexed (`documents_indexed: 2`).

## Open items

- Same as previous session log (`TEST.pdf` duplicate unprocessed by design, wiki generation deferred, chunking can straddle story boundaries, no auth on non-upload endpoints).
- Worth considering a lint/test rule catching new `OllamaClient(...)` call sites that don't pass a config-derived timeout, since this exact bug (forgetting to thread the timeout through) has now happened twice (frontend, then backend).
