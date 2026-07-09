# Session 5

**Branch:** `session-5` (merged into `main` at the end of this session)
**OpenSpec changes:** `finalize-and-ship` (archived `2026-07-08-finalize-and-ship`), `wiki-legibility-and-deploy-fixes` (archived `2026-07-09-wiki-legibility-and-deploy-fixes`)

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

## Round 3: the deferred, lower-priority items - and one real deployment gap

The user confirmed `design-dark` as the final frontend direction (the other two branches stay purely as reference, no action needed) and asked to spend the rest of the session on the three lowest-priority carried-forward items, plus asked a direct question: if AWS infra were already in place, what's actually still risky?

### Answered: real risk even with infra ready

Checked one concrete claim rather than speaking in generalities: `deploy/backup.sh` calls the `sqlite3` CLI directly, but `setup_ec2.sh`'s `apt-get install` line never installed it - a fresh Ubuntu 22.04 instance isn't guaranteed to have it, so the daily backup timer would have silently failed from day one. Fixed immediately (`apt-get install ... sqlite3`). Also flagged, without code changes needed: zero live executions of any deploy script, Certbot/DNS ordering, ongoing GPU-instance cost from the moment it launches, no monitoring/alerting, and no real backup/restore drill ever run end-to-end.

### Chunking across story boundaries - fixed, not just deferred again

Investigated the actual M1E/M2E text before assuming this needed the "re-extraction with font/heading metadata" the design.md originally called for. Found something simpler and just as reliable: Wyrd's sourcebooks repeat a running page header per story ("M1E Core • Snow on a Tombstone") on every page of that story - no font metadata needed, just a text pattern. Implemented: `pdf_extractor.py` detects this per page (`ExtractedPage.section`), `chunker.py` treats a section change as a hard break (flushed without carrying overlap forward, so a chunk never opens with the previous story's trailing sentences).

Two false-positive sources had to be filtered out before this was trustworthy, both found by testing against the real PDFs rather than trusting the regex on paper:
- The naive separator (`\W+`) matches newlines, so a table-of-contents dot-leader line ("M1E Core...........................") would consume the leader dots *and* the line break, capturing the next unrelated TOC entry as a bogus title. Fixed by excluding newlines and periods from the separator class.
- A cover page's "`<Edition> Core • <book subtitle>`" line is syntactically identical to a real running header but never repeats. Added a document-wide filter: a detected title only counts as a real section if it appears on 2+ pages.

Verified on the real M1E/M2E PDFs (not just synthetic unit tests): after both fixes, 0 chunks straddle a detected section, real transitions are still caught (e.g. pages 13→15 in M1E, "The Breach, A History of Malifaux" → "Snow on a Tombstone"), and both false-positive sources are gone from the per-page section list. Confirmed the fix isn't a no-op by reverting `chunker.py` alone and re-running the new tests - both failed with the exact "story A's tail merged into story B's first chunk" pattern the fix targets, then passed once restored.

**This only affects newly-ingested documents.** The already-ingested M1E/M2E data in `vector_db/` was chunked before this change. Applying it retroactively means re-ingestion - which changes chunk IDs and would orphan the existing `entity_mentions` rows unless entities are also re-extracted, and takes real time (the session-4 benchmark put full-document ingestion in the multi-minute range per document). Not done automatically - this is a real, semi-irreversible operation on the current dataset and is a decision for the user, not an implementation detail.

### Wiki search scaling - investigated, genuinely not an issue yet

Checked the actual implementation (`base.html`'s inline script) rather than assuming the old concern still applied: it's a per-page DOM filter, not a sitewide search - it filters category tiles on the index page and filters entities-within-one-category on a category page, which is a coherent, correctly-scoped design, not a bug. Checked real numbers against the live database: 122 entities total, 86 in the largest category (character). A `querySelectorAll` + text-scan over 86 elements per keystroke is trivially fast; even an order-of-magnitude increase (860) wouldn't produce noticeable lag. No code change made - this would be over-engineering for a scale problem that doesn't exist yet, consistent with not building for hypothetical future requirements. Worth revisiting only if a category realistically approaches the thousands.

### Threshold tuning - real evidence gathered, no blind changes made

**Dedup similarity threshold (0.7):** ranked every same-type entity-name pair in the live 122-entity database by similarity ratio to see what the threshold actually admits or excludes. Found it's well-calibrated: the one plausible near-duplicate above the threshold ("Governor-General's mansion" vs. "The Governor's Mansion," 0.756) is a real candidate worth asking about, while everything below 0.7 (Niccolò/Niño, Mara/Margaret, Gideon/Simeon, etc.) is obviously unrelated - lowering the threshold would only flood the LLM confirmation step with noise for zero recall gain. Ran `scripts/dedupe_entities.py --dry-run` against the live data to confirm the full pipeline still behaves correctly: it found "no duplicate groups" this time, including declining to merge the Governor's mansion pair - because "The Governor's Mansion" has an empty stored description, giving the LLM confirmation step insufficient evidence to confidently confirm a merge. That's the conservative, intentional behavior the design was built around (documented in session 4), not a bug - but it does mean this specific pair is a real, currently-unmerged duplicate that a human reviewer (with more context than the model had) could confirm and merge by hand if desired. Flagged for the user rather than auto-merged unilaterally.

**Dynamic-tag threshold (3 entities):** no novel tag has ever been proposed in an actual reclassification run - every entity in the real data landed in the 7 curated types. There's no real precision/recall evidence to tune this against yet; left as-is, honestly documented as untested rather than pretending a data-backed adjustment was made.

## Verification

170/170 tests passing (up from 162 earlier this session - added 3 chunker tests and 5 pdf_extractor tests covering the section-detection heuristic and both false-positive fixes). All new tests confirmed to actually catch their target bug: reverted the relevant source file, watched them fail with the real bug's exact symptom, restored the fix, watched them pass.

## Round 4: wiki legibility, real AWS deploy-blockers, and a product rename

OpenSpec change: `wiki-legibility-and-deploy-fixes` (archived `2026-07-09-wiki-legibility-and-deploy-fixes`). Prompted by three asks: make sure a document only needs to be processed once for the wiki to be fully legible, find more AWS deployment problems (beyond the sqlite3 gap from round 1), and rename the product's user-facing masthead away from "Buddharauer" (the prior project's name).

### Wiki legibility: dedup and summary generation are no longer separate manual steps

Previously, a document only needed processing *once* to get its text and entities into the store, but the wiki wasn't fully legible until someone remembered to run `scripts/dedupe_entities.py` afterward, and each entity's wiki summary was generated lazily on first page view (a real LLM-call delay for whoever visited first). Both are now automatic: `ingest_pdf()` runs a new `_prepare_wiki_data()` step after entity extraction that (1) deduplicates across the *entire* entity store, not just the newly-ingested document - a real duplicate can span documents - and (2) generates and caches a wiki summary for every entity still missing one. Order matters: dedup runs before summarization, so a summary is never generated for an entity that's about to be merged away. Both steps are wrapped in the same "enhancement, not core to success" pattern entity extraction already uses, and the wiki's on-demand generation fallback (fixed earlier this session) still covers anything left unsummarized.

### Two real, deployment-blocking bugs found by actually reading the deploy scripts

Asked to look harder at AWS deployment risk turned up two bugs that would each independently have stopped a first deploy, found by reading closely rather than skimming:

1. `setup_ec2.sh` installed `python3.11` via apt - Ubuntu 22.04 ships Python 3.10 by default and doesn't have 3.11 in its standard archives without adding the deadsnakes PPA. Checked whether the codebase actually needs 3.11 (no `match` statements, no `tomllib`, no `ExceptionGroup`) and found nothing that does - lowered the requirement to 3.10 everywhere (`setup_ec2.sh`, `pyproject.toml`, `README.md`) rather than adding a PPA dependency for no benefit.
2. `nginx-buddharauer.conf` shipped with a `listen 443 ssl` server block with no certificate - nginx validates this at config-test time, *before* Certbot ever runs, and refuses to start with "no ssl_certificate is defined." That means `setup_ec2.sh`'s own `nginx -t` call would have failed before the script even finished. Rewritten to ship HTTP-only; Certbot's standard `--nginx` workflow adds the HTTPS block and redirect itself once pointed at a working HTTP vhost - this is the documented, supported way to use it, not a workaround.

Neither could be verified by actually running `nginx -t` or `setup_ec2.sh` against a real host (no Linux nginx binary, no AWS account in this environment) - same category of gap as the earlier `systemctl`/`sqlite3` limitations. Reasoned through and fixed based on well-documented nginx/Ubuntu behavior, not silently assumed correct.

### Masthead rename: Buddharauer -> Malifaux Document Explorer

"Buddharauer" was the prior project's name and no longer fits. Renamed everywhere it's actually displayed to a user: the Gradio app's browser-tab title and on-page heading, all four wiki page `<title>` tags, the FastAPI `/docs` title, and both READMEs. Left internal infrastructure identifiers alone (systemd unit names, `/opt/buddharauer` paths, the Python package name, log messages) - those weren't part of the ask and renaming them would be a much larger, more disruptive change for no user-visible benefit.

## Verification

176/176 tests passing (up from 170 earlier this session - added 9 tests: 5 for the new dedup+summarize ingestion step, including one that reverts a monkeypatched failure to prove ingestion still succeeds, and confirmed no test anywhere asserted the old "Buddharauer" text before renaming it). Restarted backend and frontend on the final code; confirmed live: the masthead reads "Malifaux Document Explorer" in the browser tab and on-page, the wiki `<title>` reads "Wiki - Malifaux Document Explorer", chat still answers correctly, and a real wiki entity page still renders.

## State at end of session

- `session-5` merged into `main` (fast-forward, no divergence) at the end of this session.
- 9 capability specs (all synced), no active OpenSpec changes.
- `design-dark` confirmed as the final frontend direction; `design-classic`/`design-modern` intentionally kept as reference.
- Backend and frontend both restarted and smoke-tested on the final code.

## Open items carried forward

- Decide whether to re-ingest the live M1E/M2E data to benefit from the chunking-boundary fix from round 3 (changes chunk IDs; orphans existing entity_mentions unless entities are also re-extracted) - re-ingesting now would also pick up the new automatic dedup/summary step.
- Optionally hand-merge the one real, currently-unmerged duplicate found in round 3: "Governor-General's mansion" / "The Governor's Mansion" (both M1E, same place, automated dedup declined due to one having an empty description).
- Image-processing/vision-model support remains unbuilt - see the round-1 research summary above if greenlit.
- Off-host (S3) backup replication - deferred until a real AWS account exists to configure it against.
- None of the `deploy/` artifacts have been run against a real AWS account - two real bugs were found this session by close reading alone (sqlite3 install, Python version, Nginx TLS ordering); a real deploy attempt would be the next level of verification beyond that.
