## Why

Session 4 shipped the deployment artifacts (single GPU-backed EC2 instance, systemd units, Nginx reverse proxy) and the admin controls (remote service control, direct database access) and merged them to `main`. Before this becomes a real, publicly reachable site, two gaps in that work are real risks rather than nice-to-haves: the admin password (which gates arbitrary SQL execution and service start/stop) has no brute-force protection, and there is no backup of the SQLite database or vector store before the intentionally-unrestricted database browser can be used to run a destructive query against it. Both are addressable now, before a real domain and real users exist, rather than after an incident.

## What Changes

- Add rate limiting/lockout to the admin-authenticated endpoints (`/api/auth/verify`, `/api/admin/query`, `/api/documents/upload`, and the controller's `/control/*` routes) so repeated wrong-password attempts get throttled instead of allowing unlimited guesses.
- Add an automated backup mechanism for `data_storage/buddharauer.db` and the `vector_db/` directory (a systemd timer + backup script, documented in `deploy/`), so a bad admin SQL query or an accidental service mistake doesn't destroy the only copy of ingested/entity data.
- Clean up now-stale git worktrees left over from session 4's design exploration (`chat-frontend-dark` and `design-dark` are already merged into `main`; the `session2-demo` worktree still points at a pre-session-4 commit of `main`) - removing worktrees only, not their branches, and only after confirming with the user which are safe to remove.

## Capabilities

### New Capabilities

(none - this hardens existing capabilities rather than introducing new ones)

### Modified Capabilities

- `admin-controls`: add a rate-limiting/lockout requirement covering all admin-password-gated endpoints.
- `deployment`: add a backup/restore requirement for the application database and vector store.

## Impact

- `src/api/main.py`, `src/api/routes/auth.py`, `src/api/routes/admin.py`, `src/api/routes/documents.py`, `deploy/controller.py` - add rate limiting to admin-gated request handling.
- `deploy/` - new backup script + systemd timer unit, README updates documenting restore procedure.
- Local git worktrees only (no branch deletions) for cleanup, pending user confirmation on which are safe to remove.
