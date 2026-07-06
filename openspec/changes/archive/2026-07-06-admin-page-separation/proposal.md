## Why

Upload is already gated by an admin password at the API layer (`admin-gated-upload`), but the upload widget and password field still sit on the main chat page, visible to every visitor. Admin functions should live on their own page that's actually locked - not just present-but-rejected - so regular users never see admin controls at all.

## What Changes

- Add a separate `/admin` page (Gradio multi-page route) containing the upload widget.
- The admin page starts locked: only a password field + "Unlock" button are shown. Entering the correct admin password reveals the upload form; an incorrect password shows an error and keeps it hidden.
- Add a small backend endpoint to verify the admin password without performing an upload, so the frontend can gate visibility before any file is involved.
- Remove the upload widget and password field from the main chat page entirely.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `chat-api`: add an admin-password verification endpoint (separate from, but reusing the same check as, the upload endpoint).
- `chat-frontend`: the `Upload Interface` requirement changes again - upload now lives on a dedicated, password-locked admin page rather than the main chat page.

## Impact

- **Code**: `src/utils/auth.py` (new, shared password-check helper), `src/api/routes/auth.py` (new endpoint), `src/api/routes/documents.py` (reuse shared helper), `src/frontend/app.py` (multi-page restructure via `gr.Blocks.route`).
- **No change** to the existing `POST /api/documents/upload` contract - it still requires the admin password itself; this change only adds a pre-check and relocates the UI.
