## Context

`admin-controls` (session 4) intentionally gives anyone with the admin password full, unrestricted power: arbitrary SQL against the application database, and start/stop/restart of both services. That's a reasonable trust model for a single shared admin password, but only if the password itself is hard to guess by brute force and a bad query is recoverable. Neither is true yet: `verify_admin_password` (`src/utils/auth.py`) does a timing-safe comparison but has no limit on how many times it can be called, and there is no backup of `data_storage/buddharauer.db` or `vector_db/` anywhere in the deployment artifacts. This is the last hardening pass before the site in `deploy/` is pointed at a real domain.

The deployment is a single EC2 instance running one Uvicorn process per service (no `--workers`, confirmed in `deploy/buddharauer-backend.service`) and one controller process, so any solution can rely on in-process state - no distributed rate-limit store or shared cache needed.

## Goals / Non-Goals

**Goals:**
- Make brute-forcing the admin password materially harder without adding new infrastructure dependencies.
- Guarantee a recent, restorable copy of the application's data exists at all times once deployed.
- Leave the codebase and worktree list in a clean state for session 5 to build on.

**Non-Goals:**
- Multi-admin accounts, per-user permissions, or an audit log of admin actions - out of scope, not asked for.
- Off-host/cloud (e.g. S3) backup replication - local-disk backups solve the immediate risk (recovering from a bad `DELETE`/`DROP` issued through the database browser); off-host replication is a reasonable session 6+ follow-up once there's a real AWS account to configure it against.
- Rate limiting for non-admin, non-authenticated routes (`/api/chat`, `/api/documents`, the wiki) - those aren't gated by a shared secret, so brute-forcing isn't the threat model there; general DoS protection is Nginx/infra-layer, already out of this app's scope.

## Decisions

**In-memory, per-process rate limiter instead of a new dependency (e.g. `slowapi` + Redis).** The deployment is intentionally a single instance running a single process per service - there's no second Uvicorn worker or second host for state to desynchronize across. A small fixed-window lockout (e.g. 5 wrong attempts per IP within 15 minutes locks that IP out for 15 minutes) implemented as a module-level `dict[str, list[float]]` guarded by a `threading.Lock` is enough, matches this project's "plain, explicit code over premature abstraction" convention, and adds zero new dependencies. If the deployment topology ever changes to multiple workers/hosts, this would need to move to a shared store (Redis/DB-backed) - noted as a real limitation, not silently ignored.

**Apply the same limiter to both the FastAPI app and the separate `deploy/controller.py` process**, since the controller is a second, independently-reachable admin-gated surface (even though it's only reachable from the frontend's server-side calls in the real topology, not directly from the internet) - defense in depth costs nothing here since it's the same few lines of code.

**Lock out by client IP, not by password attempted.** Locking by IP is simpler, doesn't require storing/hashing attempted passwords, and matches the actual threat (one attacker hammering the endpoint) rather than a threat that doesn't apply here (this app has exactly one admin password, not an account enumeration surface).

**Backups via a systemd timer + shell script, not application code.** Backing up is an operational concern that shouldn't run inside the request-serving process. `sqlite3 <path> ".backup <dest>"` is SQLite's own supported hot-backup mechanism (safe to run against a live, in-use database, unlike a raw file copy). The `vector_db/` directory (ChromaDB's on-disk store) gets a straightforward `tar`-and-copy, since Chroma has no equivalent single-file hot-backup command. A daily systemd timer runs the script, keeping the last 7 days locally in `/opt/buddharauer/backups/`.

## Risks / Trade-offs

- [Risk] An attacker distributes attempts across many IPs (botnet), defeating per-IP lockout. → Out of scope for a single small self-hosted app; Nginx/AWS security-group-level protections are the appropriate layer for that threat, not this app's admin auth.
- [Risk] Local-disk-only backups don't survive the EC2 instance itself being destroyed (e.g. accidental termination). → Documented explicitly as a known gap in `deploy/README.md`, with off-host replication (S3) flagged as a natural follow-up once a real AWS account exists to configure it against - not silently glossed over.
- [Risk] Removing a git worktree without checking for uncommitted changes could lose work. → Each worktree gets `git status` checked before removal, and only worktrees whose branch is fully merged into `main` (or explicitly confirmed stale by the user) are removed; branches themselves are never deleted, only the local worktree checkout.

## Migration Plan

1. Add the rate limiter as a small shared utility (`src/utils/rate_limiter.py`), wire it into `auth.py`, `admin.py`, `documents.py` (upload), and `deploy/controller.py`.
2. Add `deploy/backup.sh` and a `buddharauer-backup.timer` + `.service` pair; document manual restore steps in `deploy/README.md`.
3. Run the full test suite plus a live rate-limit check (hammer `/api/auth/verify` with a wrong password N+1 times, confirm the N+1th attempt is rejected before even reaching the password comparison) and a live backup/restore smoke test against local temp storage.
4. Confirm with the user which stale worktrees are safe to remove, then remove them (worktrees only).

## Open Questions

- Should the lockout window/threshold (5 attempts / 15 min, proposed above) be configurable via `config.yaml`, or is a hardcoded sane default acceptable for now? Defaulting to hardcoded unless the user wants it tunable - keeps this change small.
