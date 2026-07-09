# Session 4

**Branch:** `session-4` (merged into `main` at the end of this session)
**OpenSpec changes:** `wiki-taxonomy-and-navigation` (archived `2026-07-08-wiki-taxonomy-and-navigation`), `entity-dedup-and-session-isolation` (archived `2026-07-08-entity-dedup-and-session-isolation`), `deployment-and-admin-controls` (archived `2026-07-08-deployment-and-admin-controls`)

## What shipped

- **Fixed the broken wiki-to-chat link**: `base.html`'s top-nav "Chat" link was a relative `href="/"`, but the wiki is served by the backend (port 8000) while chat is a separate Gradio app (port 7860) - a genuinely different origin. `curl http://localhost:8000/` confirmed a 404. Fixed with a new `frontend.public_url` config value (defaults to `http://localhost:{frontend.port}`), passed into every wiki route's template context, so the link is now absolute.
- **Expanded the entity taxonomy** from 4 types (character/faction/item/location) to 7, adding `real-person` (game credits/authors), `creature` (undead/constructs/monsters), and `event`. `entity_extractor.py`'s live extraction prompt now uses all 7 for future uploads.
- **Threshold-gated dynamic tagging**: during reclassification, the model can propose a genuinely novel tag beyond the curated 7, but it only survives (becomes a real category) if at least 3 entities land in it - otherwise those entities revert to their prior type. Keeps the taxonomy from accumulating one-off noise.
- **One-off reclassification pass** (`scripts/reclassify_entities.py`) over the existing 133 entities, using each entity's stored name/description rather than re-reading source PDFs - a few minutes of small concurrent LLM calls instead of hours of re-extraction.
- **Per-type entity colors**: red/purple/gray/gold/teal per curated type instead of one bright red for every entity, with `real-person` deliberately muted/desaturated to read as meta content rather than story cast.
- **Wiki landing page**: `/wiki` now shows total entity count, document count, and a per-category breakdown above the category browsing, instead of directly being the category index. Dropped the old "first 5 entities per category" preview from the index - that content now lives only on category pages.

## Getting the reclassification prompt right took two real correction rounds

First run (discarded, DB restored from backup before persisting): the initial prompt ("real-person = a real-world person credited in the text") over-triggered on fictional characters who merely *had* an in-story occupation - "Jacob Samuels, the owner of Ringside", "Dr. Victor Ramos, president of the Miners and Steamfitters Union", "Michael Rutledge, a convicted mass murderer" all got mistyped as `real-person`. Fixed by rewriting the prompt to require *explicit book-credit language* ("Author of the M1E Core", "Writer", "Producer") and to explicitly say an in-story occupation does NOT make someone a real person.

Second run (also discarded, restored again): with the tightened prompt, actual fictional characters with descriptions were now correctly classified - but every entity with a **blank description** still got mistyped as `real-person`, 100% of the time. With no other signal, the model defaulted to "sounds like a plausible name -> real person" regardless of an explicit "if unsure, keep the current type" instruction in the prompt. Since this failure mode was completely consistent, the real fix was in code, not more prompt-wrangling: `reclassify_entities()` now skips the LLM call entirely for any entity with an empty/blank description and just keeps its original type - cheaper and more reliable than hoping the model restrains itself.

Third run (kept): exactly 10 real book credits moved to `real-person` (zero false positives - Nathan Caroland, Eric Johns, Kelly Brumley, and the rest of the M1E Core credits list), 4 legitimate non-human entities moved to `creature` (Sybelle, December, Takashi, Philip Tombers - a desiccated test-subject corpse), one location got correctly reclassified to faction, and all ambiguous/blank-description entities stayed exactly where they were. Spot-checked in the running wiki via Playwright.

## Other findings

- `data/MalifauxStories_TEST.pdf` is byte-identical to M1E (confirmed via `md5sum` - same checksum). Nothing new to ingest; both real documents (M1E, M2E) were already fully processed going into this session.

## Verification

120/120 tests passing (up from 108 at the end of session 3 - added reclassification unit/integration tests, config tests for `public_url`, entity-type/color regression tests). Backend + frontend restarted; live Playwright pass confirmed: the chat link is absolute and actually resolves (200, not 404), category tiles render in genuinely distinct colors, `real-person` is visibly muted relative to `character`, the landing page shows correct live stats (133 entities, 2 documents, per-category counts), and the reclassified data renders correctly in the running wiki (`real-person` category contains exactly the 10 credits and nothing else; `character` category still correctly contains Jacob Samuels/Dr. Victor Ramos/Michael Rutledge).

## Round 2: `entity-dedup-and-session-isolation`

After the taxonomy/navigation round shipped, the user asked to clear the remaining open items from prior sessions: the shared-conversation-ID bug, chat speed (further), and entity fragmentation. Two of the three carried a real trade-off or risk, so those were checked with the user before proceeding rather than decided unilaterally; the third (chunk boundaries in the multi-story anthologies) was explicitly deferred as too high-cost/uncertain for this round.

### Fixed: shared conversation ID

`src/frontend/app.py` had `conversation_id = gr.State(str(uuid.uuid4()))` - `gr.State`'s value is evaluated once at app-build time, not per session, so every browser session shared one conversation history. Gradio's own docs describe the fix: pass a callable and it's invoked fresh per session load. One-line change (`gr.State(lambda: str(uuid.uuid4()))`), verified live: two independent Playwright browser contexts submitting messages concurrently now show two distinct conversation IDs in the backend's query log (previously would have been identical).

### Investigated and rejected: a faster chat model

Pulled `llama3.2:1b` (vs. the current `llama3.2:latest`, 3B) and benchmarked both against the *actual* live retriever's real output for two real questions ("Who is Lady Justice?", "What is the Ortega family known for?") - not synthetic filler text, since an earlier synthetic-context test had produced a misleading hallucination ("Cadian Empire", a Warhammer 40K term, not Malifaux) that turned out to be an artifact of the test itself having no real grounding content. With real context, prompt evaluation was ~3x faster (6-7s vs 18-23s), but the 1B model hallucinated on both real questions anyway - confusing Perdita's siblings with monster types ("Sonnia (a Gremlin)", "Santiago (a Peacebringer)"). The 3B model stayed coherent and grounded on identical context both times. Speed isn't worth trading for fabricated lore in a RAG app whose core requirement is grounded answers - no model change ships; documented as a considered-and-rejected option rather than silently dropped.

### Entity deduplication - the approach had to be redesigned after the first attempt failed completely

First attempt: ask the model to cluster an entire type's entity list (e.g. all 97 characters) into duplicate groups in one call. Result: 10 proposed merge groups, **all of them wrong** - it merged three different real book-credit authors together ("Chrissy Monfette" absorbing "Eric Johns" and "Graeme Stevenson"), and merged unrelated locations ("Malifaux Station" absorbing "Malifaux" the city itself). It completely missed the actual known duplicates ("Molly Squidpiddge" variants, "Samael" variants) while inventing wrong ones. Discarded before persisting (dry-run only; DB was never touched).

Rewrote the approach: generate candidate pairs first via a cheap Python string-similarity pre-filter (exact-normalized-name match or substring match or a `difflib` ratio >= 0.7) within each type, then ask the model a narrow yes/no question about each *specific pair* rather than open-ended whole-list clustering, then union transitively-confirmed pairs (e.g. "McMourning" <-> "Douglas McMourning" <-> "Dr. Douglas McMourning" chains into one group) via a small union-find structure. This produced 9 merge groups on the real data, all of which checked out on inspection - exact-name duplicate rows (same name, extracted separately per document) merged with zero LLM calls needed (no ambiguity), plus the two originally-identified real fragmentation cases ("Molly Squidpiddge"/"Molly Squidpiddge (again)", and the 4-way "McMourning" chain). Notably, the model correctly declined to merge some superficially-similar candidates it wasn't confident about (e.g. two different "Samael"-named characters with inconsistent descriptions, "Sonnia"/"Sonnia Squidpiddge"/"Sonnia Criid") rather than forcing a merge - the conservative behavior the design was aiming for.

Applied via `scripts/dedupe_entities.py --dry-run` (reviewed) then for real, after backing up the database. 133 -> 122 entities (11 merged into 9 groups). Verified live in the wiki: only one "Molly Squidpiddge" entry remains, "Dr. Douglas McMourning" now carries 217 consolidated mentions (up from being split across 4 rows) with its fullest description intact, landing page stats correctly show 122.

## Verification

134/134 tests passing (up from 120 at the end of round 1 - added `merge_entities` tests, candidate-pair/union-find unit tests, pairwise-confirmation integration tests with fake Ollama clients covering transitive chains and failure handling). Backend + frontend restarted after each round; live Playwright/query-log verification confirmed both the session-isolation fix and the deduplicated wiki data.

## Round 3: frontend design exploration + deployment/admin controls

The user flagged the frontend (especially the wiki) as still visually rough, and asked for a few different design directions to compare, plus asked to start planning real AWS deployment with admin controls (start/stop the backend, direct database access).

### Three design-exploration branches

Branched off `session-4` (not merged into it): `design-classic`, `design-modern`, `design-dark`. Each restyles both the wiki (`base.html`) and the chat frontend (a matching `gr.Theme` + CSS) as one cohesive identity, sharing the same underlying data:

- **`design-classic`**: a refined version of the app's original serif/dark-red look - warm parchment background, Playfair Display headlines, deepened burgundy palette.
- **`design-modern`**: a clean, contemporary light theme - Inter sans-serif, blue accent, card-based surfaces with soft shadows.
- **`design-dark`**: a full dark mode leaning into Malifaux's gothic-horror atmosphere - near-black background, Cinzel display-serif titles, crimson/gold accents. Needed a second pass after the first screenshot showed secondary buttons ("Clear chat", "Refresh document list") and placeholder text staying illegibly light-on-dark - Gradio's secondary-button and prose-text color variables weren't covered by the first theme override and had to be added explicitly.

All three verified visually via Playwright screenshots, 134/134 tests passing on each, all pushed to `origin`.

### Deployment: single GPU-backed EC2 instance, not ECS/Fargate

The user's instruction was conditional: use ECS/Fargate only if it would actually speed up chat responses. Checked the premise directly rather than guessing: **AWS Fargate cannot attach a GPU at all** - a hard platform limitation (GPU support on ECS requires the EC2 launch type, not Fargate). Since this session's earlier diagnosis already pinned the "thinking" delay on CPU-bound Ollama inference, container orchestration was never going to be the lever that helps - only GPU compute is. So the deployment artifacts target a single `g4dn.xlarge`-class EC2 instance instead: systemd units for the backend/frontend, an Nginx reverse proxy (path-routing `/api/*` and `/wiki*` to the backend, everything else to the frontend, TLS via Certbot), a security-group policy exposing only 80/443/restricted-SSH, and a setup script. None of this was run against a real AWS account (no credentials in this environment) - it's reviewed-but-unexecuted infrastructure for the user to apply.

### Admin controls: database browser + remote service control

Two new sections on the existing password-gated admin page:

- **Database Browser**: a new admin-gated `POST /api/admin/query` endpoint runs arbitrary SQL against the SQLite database and returns results - deliberately unrestricted (no read-only mode), since "direct database access" means direct access and the admin password is the same trust boundary PDF upload already has.
- **Service Control**: start/stop/restart/status for the backend and frontend from the browser, without SSH. A live process cleanly restarting *itself* mid-HTTP-request is architecturally awkward, so this goes through a separate, minimal `buddharauer-controller` process (its own systemd unit) holding a `sudoers.d` rule scoped to *exactly* `systemctl {start,stop,restart}` on the app's two units - nothing else, never reachable from outside the instance.

Verified locally as far as this Windows dev machine allows: the controller's request validation (auth gating, service/action whitelisting, systemctl-failure handling) is covered by 7 mocked unit tests, and the admin page's UI was verified live via Playwright (unlock, run a real SQL query against the actual entity data, trigger a status refresh). The actual `systemctl` execution can only be verified on a real Linux host - confirmed the auth path works correctly (wrong password never reaches the subprocess call; correct password does) but the command itself predictably fails with "command not found" on Windows, which is expected and not a bug.

## Verification

145/145 tests passing (up from 134 at the end of round 2 - added admin-query and controller tests). All three design branches and the deployment/admin-controls work verified via live Playwright passes against locally-running instances.

## Round 4: chat frontend theme adoption, document-processing estimate, grounded-vs-inferred prompting

The user picked `design-dark` as the winning direction (already merged into `session-4` in round 3) and asked for the same style to be carried into the chat frontend specifically, then asked two scoping questions about the deployed system and one more prompt-engineering request before wrapping the session.

### Chat frontend restyled to match `design-dark`

New branch `chat-frontend-dark` off `session-4`: added a matching `gr.themes.Base` override (Cinzel/EB Garamond, crimson/gold accents) and a CSS block to `src/frontend/app.py`. Needed one extra pass after the first screenshot: `gr.Dataframe` doesn't inherit the theme's dark palette at all (renders white regardless of theme config) and had to be forced dark via explicit CSS targeting `.table-wrap`. Verified via Playwright screenshots of a populated chat with a citation selected, then merged back into `session-4` (clean merge, no conflicts) at the end of this round.

### Document-processing time estimate

The user asked how long ingesting a new document takes. Rather than reuse older, pre-optimization figures from earlier sessions, ran a real, isolated benchmark (temp-storage `DocumentRegistry`/`VectorStore`/`EntityStore`, a real 30-page slice of the M1E PDF) timing each pipeline stage separately: PDF extraction, chunking, embedding, vector insert, and entity extraction. Entity extraction needed a re-run with a longer client timeout (600s) after the first attempt's batches all hit the config's normal 180s request timeout and returned a false "0 entities" reading. Extrapolated the clean per-stage numbers to a full ~700-page document using the actual 8-worker concurrency model (wall-clock ≈ `ceil(batches / 8) × per-batch time`, not naive linear scaling), giving the user a real estimate broken down by stage instead of a guess.

### Confirmed: fully local/tokenless, no image processing yet

Two scoping questions, answered by inspection rather than assumption: grepped the whole pipeline for any image/vision usage (`llava`, `vision`, `get_pixmap`, `get_images`) and found none - `pdf_extractor.py` only ever calls `page.get_text()`. Confirmed the entire stack (embeddings, chat, entity extraction) runs through local Ollama with no external API keys, so the "tokenless" framing holds today and continues to hold once deployed to the user's own AWS instance. `llava:latest` and `llama3.2-vision:latest` are already pulled locally from earlier session exploration but are not wired into anything - noted as a real option, not built, per the user's explicit instruction to defer it to session 5 (see Open items).

### Grounded-vs-inferred answer structure

`src/rag/prompt_builder.py`'s `SYSTEM_PROMPT` now explicitly instructs the model to structure every answer as a `**From the documents:**` section (facts directly traceable to the attached citations) followed by an optional `Interpretation:` section (reasoning that goes beyond what the context explicitly states, omitted entirely when not needed). The citations mechanism itself was already fully programmatic (attached from retrieved-chunk metadata, never LLM-generated) - this change is about making the *answer text* itself legible about what's grounded vs. inferred. Existing tests only assert message-list structure, not exact prompt wording, so no test changes were needed. Verified live against the real vector store and Ollama with "Who is Lady Justice?" - the model followed the two-part structure correctly on the first attempt, correctly separating stated facts (her role as Death Marshal captain) from actual inference (reading her line "Do I even have to be here?" as implying doubt about her role).

## Verification

145/145 tests passing (full suite - unit, integration, e2e) after the `chat-frontend-dark` merge and the prompt change. Also ran a temp-storage benchmark script for the document-processing estimate and a live retriever/Ollama round-trip against the real vector store for the prompt-structure verification.

## State at end of session

- `session-4` merged into `main` and pushed to `origin` - this is the first session-4 round to land on `main`.
- `chat-frontend-dark` merged into `session-4` (and therefore into `main`); `design-classic` and `design-modern` remain separate, unmerged exploration branches on `origin` in case the user wants to revisit them later.
- `deploy/controller.py`, the AWS EC2 setup script, and the admin database/service-control panel all shipped as part of this merge - still unexercised against a real AWS account (see open items).
- The `../rauer-rebuild-session2-demo` worktree from session 3 still exists on disk (not removed) - stale, harmless.
- `llama3.2:1b`, `llava:latest`, and `llama3.2-vision:latest` remain pulled locally but are not referenced by any config.

## Open items carried forward

- **Session 5: look into an image-processing/vision model.** The current pipeline is text-only (`page.get_text()`); `llava:latest` and `llama3.2-vision:latest` are already pulled locally and unused. User explicitly asked to defer any action on this until session 5 starts - do not build against it before then.
- None of the `deploy/` artifacts have been exercised against a real AWS account - review before applying to a live server.
- `design-classic` and `design-modern` remain unmerged, undecided alternatives to the now-adopted dark theme.
- Chunking can straddle story boundaries in the M1E/M2E anthologies - deferred again (needs font/heading-aware re-extraction, re-chunking, and re-embedding; heuristic boundary detection is inherently imperfect).
- Client-side wiki search (session 3) doesn't scale indefinitely - revisit if entity count grows an order of magnitude.
- The dynamic-tag threshold (3 entities) and dedup similarity threshold (0.7) are untuned judgment calls - fine at current scale, worth revisiting as more documents are ingested.
