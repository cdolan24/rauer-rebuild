## Context

Document upload (`POST /api/documents/upload`) and its frontend widget are currently open to any caller. The MVP explicitly deferred real multi-user auth as future work. This change adds just enough of a gate to stop uninvited uploads during evaluation, without building the full auth system.

## Goals / Non-Goals

**Goals:**
- Only requests carrying the correct shared admin password can trigger ingestion of a new PDF.
- Frontend collects the password and surfaces a clear error on mismatch, rather than looking broken.

**Non-Goals:**
- No user accounts, roles, sessions, or tokens.
- No protection on any other endpoint (chat, search, document read) - those stay open for evaluation.
- Not a substitute for real secrets management - `admin_password` lives in local `config.yaml` (already gitignored), same trust level as the rest of this local-first MVP.

## Decisions

**1. Password carried as a multipart form field on the upload request, not a header.**
The upload endpoint already accepts `multipart/form-data` for the file; adding `admin_password` as a second form field keeps the client code (and Gradio's `File` component) simple, with no separate auth header/session plumbing.

**2. Compare with `hmac.compare_digest`, not `==`.**
Even for a low-stakes local gate, constant-time comparison is a one-line change that avoids a cheap, unnecessary timing-attack surface.

**3. Config-driven secret (`auth.admin_password`), no default value shipped.**
`config.example.yaml` documents the field with a placeholder and a comment to set a real value; `load_config` treats a missing/placeholder password as "upload disabled" (reject all uploads) rather than silently accepting an empty string, so a forgotten config doesn't leave the gate open.

## Risks / Trade-offs

- **[Risk]** A shared password is weak protection (no per-user accountability, no rotation story) → **Mitigation**: explicitly scoped as a stopgap for the evaluation stage; proper auth is separate future work.
- **[Risk]** Password travels in a plain form field → **Mitigation**: acceptable for local-only `http://localhost` use; would need TLS + a stronger scheme before any real deployment.
