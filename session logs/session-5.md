# Session 5

**Branch:** `session-5` (off `main`, which now includes all of session 4's merged work)
**OpenSpec changes:** `finalize-and-ship` (archived `2026-07-08-finalize-and-ship`)

## What shipped

Session 4 left two real gaps in the admin-controls/deployment work that needed closing before the app is pointed at a real public domain: the admin password (which gates arbitrary SQL execution and service start/stop) had no brute-force protection, and there was no backup of the application database or vector store before a destructive admin query could be run against them. Scoped both through a proper OpenSpec change (`finalize-and-ship`) rather than just patching code directly, since both are spec-level behavior changes to the existing `admin-controls` and `deployment` capabilities.

### Admin endpoint rate limiting

`src/utils/rate_limiter.py`: an in-memory, per-client-IP fixed-window lockout (5 wrong attempts / 15 minutes), guarded by a `threading.Lock`. No new dependency (no Redis) - the deployment is a single process per service, so in-process state is sufficient; noted explicitly in the design as a limitation if that topology ever changes. Wired into all four admin-password-gated surfaces via a shared `check_admin_password()` helper in `src/utils/auth.py`: `/api/auth/verify`, `/api/admin/query`, `/api/documents/upload`, and the separate `deploy/controller.py` process's `/control/*` routes. Lockout is checked *before* the password comparison, so a locked-out client is rejected even with the correct password.

Caught a real test-isolation bug while wiring this in: `deploy/controller.py`'s FastAPI `app` and its rate limiter are module-level singletons (correct for its real deployment as one long-lived systemd process), but the existing `test_controller.py` fixture reused that same module-level state across every test in the file - repeated wrong-password tests would have silently accumulated toward the lockout threshold and could eventually break a later test in the same run. Fixed by resetting the limiter to a fresh instance in the fixture, since the *codebase's* other rate limiter (the FastAPI app's, created per-`lifespan()`) is naturally test-isolated but the controller's is not.

Verified live: restarted the real backend, sent 5 wrong passwords to `/api/auth/verify`, confirmed the 6th attempt - even with the actual correct password - was rejected with "Too many failed attempts."

### Automated backups

`deploy/backup.sh` (run daily by a new `buddharauer-backup.timer`): a consistent SQLite snapshot via `.backup` (SQLite's own safe hot-backup mechanism, not a raw file copy) plus a `tar` snapshot of the vector store, both written to a local backups directory with 7-day retention. `setup_ec2.sh` now installs and enables the timer alongside the app's other systemd units. Documented the restore procedure and one honest limitation in `deploy/README.md`: this is local-disk-only, so it doesn't protect against losing the EC2 instance itself - off-host (S3) replication is flagged as a natural follow-up once there's a real AWS account to configure it against, not silently glossed over.

Verified what could be verified on this Windows dev machine: the tar snapshot/restore round-trip end-to-end (real files in, real files out, byte-identical), and the SQLite online-backup mechanism itself (via Python's `Connection.backup()`, the same underlying mechanism the CLI's `.backup` command uses) against a real database. The `backup.sh` script's exact `sqlite3` CLI invocation could not be run here - no `sqlite3` binary on this machine - the same Windows/Linux gap session 4 hit with `systemctl`; the script's shell syntax was still checked with `bash -n`.

## Verification

157/157 tests passing (up from 145 at the end of session 4 - added rate limiter unit tests, `check_admin_password` unit tests, and lockout integration tests against the real auth/admin/controller endpoints).

## Repo cleanup

Removed the `../rauer-rebuild-session2-demo` git worktree (stale since session 3, pointed at a pre-session-4 commit of `main`). Checked all five session-4-era worktrees for uncommitted work first (all clean). Left `chat-frontend-dark` and `design-dark` worktrees running even though both branches are already fully merged into `main`, and left `design-classic`/`design-modern` running as still-undecided alternatives - user's call, not removed.

## Bonus: image-processing model research (investigation only, not built)

User asked to look into vision/image-processing models that could eventually process comic-book-style or heavily-illustrated PDFs - explicitly as research to inform session 5's carried-forward item from last session's log, not something to build yet.

**Findings:** the two models already pulled locally (`llava:latest`, `llama3.2-vision:latest`) are usable but not the strongest local options for this specifically - by 2026, `qwen2.5vl:7b` and MiniCPM-V 4.5 both beat them on document/OCR-style benchmarks despite being smaller (rough ranking found: Qwen-VL family ≳ MiniCPM-V 4.5 > Llama 3.2 Vision 11B > LLaVA 1.6). More importantly, comic-page transcription is a genuinely different problem than general image captioning: published research (Oxford VGG's "Magi" project, "The Manga Whisperer") treats it as a multi-stage pipeline - panel detection, reading-order sorting, speech-bubble detection, then OCR on bubble text - because a single "describe this page" call to a generalist vision model reliably handles scene/character description but is **not** reliable for verbatim speech-bubble dialogue transcription.

**If this gets built later:** start with `qwen2.5vl:7b` for description/captioning (better OCR accuracy than llava, smaller than llama3.2-vision-11B); add a new `src/pipeline/image_extractor.py` alongside `pdf_extractor.py` that renders each page via PyMuPDF's `get_pixmap()` and prompts the vision model for scene description + any legible text; feed that into the vector store as a separate, explicitly lower-confidence content stream (e.g. citation metadata tagged `source_type: "visual_description"` vs. today's `"extracted_text"`), so the chat's existing "From the documents:" / "Interpretation:" answer structure can treat visually-derived citations with appropriately lower trust rather than silently blending two very different reliability tiers. Nothing here was implemented - this is background for whenever the user wants to greenlight it.

## Round 2: full-repo bug and bloat review

Asked to review the whole repo for bugs, cut as much bloat as possible, and close out whatever OpenSpec housekeeping remained. Went through every module in `src/` (database, pipeline, rag, api, wiki, frontend, utils) by hand after an initial exploratory sub-agent audit stalled and failed - re-ran the review directly instead of retrying the agent.

### Bugs fixed

- **`src/wiki/routes.py`**: a not-yet-summarized entity page threw an unhandled `OllamaError` (500) whenever Ollama was unreachable, even though `entity.html` already has a `entity.summary or entity.description` fallback for exactly this case. Now catches `OllamaError` around the lazy summary-generation call and lets the page render with the description instead. Confirmed this was a real, reachable bug (not just theoretical) by reverting the fix and re-running the new regression test - it failed with the exact traceback a live Ollama outage would produce, then passed once the fix was restored.
- **`src/frontend/api_client.py`**: every admin-gated call (`upload_document`, `run_admin_query`, `ControllerClient.control/status`, and `verify_admin_password`, which previously didn't surface a reason at all) hardcoded "Incorrect admin password" on any 401 response. This silently swallowed the rate limiter's real "Too many failed attempts - try again later" message added earlier this session - a locked-out admin would be told they mistyped the password, not that they need to wait. Now extracts the backend's actual `detail` field. Verified live against the real running backend (not mocked): 5 wrong passwords followed by the correct one now correctly reports the lockout message. `src/frontend/api_client.py` had no test file at all before this - added `tests/unit/test_api_client.py`.

### Bloat cut

- Deleted `requirements.txt` - it was a word-for-word duplicate of `pyproject.toml`'s dependency list. `setup_ec2.sh` and the README now install via `pip install .` (verified with `pip install --dry-run .` that packaging still resolves correctly).
- Removed `QueryLogger.count()` - confirmed via repo-wide grep it was called nowhere, not even in tests.
- Removed a duplicate "Extracted N entities" log line in `ingest.py` (`entity_extractor.py` already logs the same thing).
- README.md had two stale problems: it told a fresh setup to `ollama pull qwen2.5:latest`, a model referenced nowhere else in the codebase (leftover from an earlier, since-abandoned model choice), and it linked to `openspec/changes/rebuild-mvp/`, which has been archived to `openspec/changes/archive/2026-07-06-rebuild-mvp/` since before this session even started. Both fixed.
- Considered removing `EntityStore.list_by_document()` (unused in application code) but confirmed it's genuinely exercised across 5 test call sites as a real verification tool - not bloat, left alone. Good reminder that "no caller in `src/`" alone isn't sufficient evidence before deleting something.

### OpenSpec housekeeping

All 9 capability specs (`admin-controls`, `chat-api`, `chat-frontend`, `deployment`, `document-ingestion`, `entity-extraction`, `pdf-citations`, `rag-chat`, `wiki`) still had literal "TBD - created by archiving/syncing change X. Update Purpose after archive" placeholders in their Purpose sections - never actually filled in since whichever change first generated each spec. Wrote a real one-paragraph purpose for each. No active OpenSpec changes existed to work through (`openspec list` was already empty); the handful of archived changes with unchecked final "commit and push" checkboxes are stale bookkeeping only - the actual work they describe was already completed and verified per those sessions' logs, just never checked off before archiving. Left those as historical record rather than editing archived changes after the fact.

## Verification

162/162 tests passing (up from 157 earlier this session - added a wiki-summary-fallback regression test and 4 new `api_client` tests). Restarted both the backend and frontend on the fixed code and smoke-tested both (`/`, `/admin` both return 200); live-verified the lockout-message fix against the real backend with an unmocked `ApiClient`.

## State at end of session

- `session-5` branch off `main`, holding the rate-limiting/backup work, the bug fixes, the bloat cleanup, and the spec documentation pass; not yet merged to `main`.
- 9 capability specs (all synced, all with real Purpose statements now), no active OpenSpec changes.
- Backend and frontend both restarted on this session's final code and smoke-tested.
- `../rauer-rebuild-session2-demo` worktree removed; the four other session-4-era worktrees (`chat-frontend-dark`, `design-dark`, `design-classic`, `design-modern`) remain, all clean.

## Open items carried forward

- Merge `session-5` into `main` when the user is ready (not done automatically this session, unlike session 4's explicit merge instruction).
- Image-processing/vision-model support remains unbuilt - see the research summary above if greenlit.
- `design-classic` and `design-modern` remain unmerged, undecided alternatives to the adopted dark theme.
- Off-host (S3) backup replication - deferred until a real AWS account exists to configure it against.
- Chunking can straddle story boundaries in the M1E/M2E anthologies - still deferred (unchanged from session 4).
- Client-side wiki search doesn't scale indefinitely - revisit if entity count grows an order of magnitude (unchanged from session 4).
- The dynamic-tag threshold (3 entities) and dedup similarity threshold (0.7) remain untuned judgment calls (unchanged from session 4).
