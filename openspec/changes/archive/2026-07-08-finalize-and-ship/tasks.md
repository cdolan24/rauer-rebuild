## 1. Rate limiter utility

- [x] 1.1 Add `src/utils/rate_limiter.py`: an in-memory, per-client-IP fixed-window lockout (`record_failure(key)`, `is_locked_out(key)`, `record_success(key)` clearing state), guarded by a `threading.Lock`, with configurable threshold/window (defaulting to 5 attempts / 15 minutes).
- [x] 1.2 Unit tests: lockout triggers after N failures, resets after the window elapses, a success does not count as a failure and does not clear an existing lockout early.

## 2. Wire the rate limiter into admin-gated endpoints

- [x] 2.1 `src/api/routes/auth.py` (`/api/auth/verify`): check lockout before comparing the password; record failure/success.
- [x] 2.2 `src/api/routes/admin.py` (`/api/admin/query`): same treatment.
- [x] 2.3 `src/api/routes/documents.py` (`/api/documents/upload`): same treatment.
- [x] 2.4 `deploy/controller.py` (`/control/*`): same treatment, independent lockout state from the main API process.
- [x] 2.5 Integration tests: a locked-out client is rejected even with the correct password on each of the four endpoints; an unlocked client with the correct password succeeds normally.

## 3. Backup mechanism

- [x] 3.1 `deploy/backup.sh`: `sqlite3 <data_storage_path> ".backup <dest>/buddharauer-<timestamp>.db"` plus a `tar` snapshot of `vector_db/`, written to a configurable backup directory; prune snapshots older than 7 days.
- [x] 3.2 `deploy/buddharauer-backup.service` + `deploy/buddharauer-backup.timer` (daily, e.g. `OnCalendar=daily`), referencing `backup.sh`.
- [x] 3.3 Add backup/restore steps to `deploy/README.md`: what gets backed up, where, retention, and the exact restore procedure (stop services, restore the `.db` file and `vector_db/` snapshot, restart services).
- [x] 3.4 `setup_ec2.sh`: install the new timer/service units and enable the timer (not just the app services).

## 4. Verification

- [x] 4.1 Run the full test suite (`pytest tests`) and confirm no regressions.
- [x] 4.2 Live-verify rate limiting: hammer `/api/auth/verify` with N+1 wrong passwords against a locally running backend, confirm the N+1th (and a subsequent correct-password attempt within the window) are both rejected, and confirm the lockout clears after the window.
- [x] 4.3 Live-verify the backup script end-to-end against a temp copy of the real `data_storage`/`vector_db`: run it, confirm a snapshot appears, corrupt/delete the working copy, restore from the snapshot, confirm the app reads the restored data correctly.
- [x] 4.4 Update the session 5 log with what shipped and any open items.

## 5. Repo cleanup (confirm with user before removing anything)

- [x] 5.1 Check `git status` in each of the `chat-frontend-dark`, `design-dark`, and `session2-demo` worktrees for uncommitted work.
- [x] 5.2 Confirm with the user which worktrees are safe to remove (branches already merged into `main`, or explicitly no-longer-needed), then remove only those worktrees - never delete the underlying branches without separate explicit confirmation.
