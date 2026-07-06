## Why

The MVP's `POST /api/documents/upload` endpoint and the frontend's upload widget are open to anyone who can reach them. In an evaluation/demo setting this means any visitor could ingest arbitrary PDFs into the shared vector database. A lightweight admin gate is enough to prevent that without building full user-account infrastructure this early.

## What Changes

- Require a shared admin password on document upload, both at the API layer and in the frontend UI.
- Reject uploads without the correct password with a 401 response; the frontend surfaces this as a clear error rather than a silent failure.
- Add an `auth.admin_password` config value (local-only, not a real secrets manager - appropriate for this stage).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `chat-api`: the `Document Upload Endpoint` requirement changes - upload now requires a correct admin password, and rejects the request otherwise.
- `chat-frontend`: the `Upload Interface` requirement changes - the frontend now collects an admin password alongside the file and surfaces auth failures.

## Impact

- **Code**: `src/api/routes/documents.py` (upload endpoint), `src/utils/config.py` (new `auth` section), `src/frontend/app.py` / `src/frontend/api_client.py` (password field + error surfacing).
- **Config**: `config.yaml` / `config.example.yaml` gain an `auth.admin_password` value.
- **Non-goals**: no user accounts, no session/token management, no protection on any endpoint other than upload - this is intentionally minimal for the current evaluation stage.
