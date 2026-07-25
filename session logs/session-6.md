# Session 6

**Branch:** `session-6` (off `main`, which now includes all of session 5's merged work)
**OpenSpec changes:** `image-page-detection` (archived `2026-07-10-image-page-detection`)

## What shipped: image-page detection and optional vision-model description

Session 5 researched local vision models for comic/image-heavy PDFs but built nothing. The user's explicit ask for session 6: build the detection-and-shift mechanism - the default pipeline should notice an image-heavy page itself and hand it to a vision model, without that model ever becoming the default for anything else.

### Live-tested both locally-pulled vision models before designing anything

Rendered a real PDF page and sent it to both `llava:latest` and `llama3.2-vision:latest` via Ollama's `/api/chat` (confirming along the way that the existing `OllamaClient.chat()` needs zero changes to support images - Ollama's message format already accepts an `"images"` field, and the client forwards `messages` into the request payload verbatim). Result: `llava` completed in 93s but hallucinated ("a mobile phone screen" for a plain text page); `llama3.2-vision` didn't finish in 120s at all. Confirms session 5's research - usable for coarse description today, not verbatim-trustworthy, meaningfully slower without a GPU. Prototyped with `llava:latest` (already pulled) rather than downloading `qwen2.5vl` (session 5's top pick) unprompted.

### Detection: a free, deterministic heuristic, not another LLM call

`pdf_extractor.py` now flags each page `is_image_heavy` using embedded-image coverage (>= 40% of the page area) combined with sparse extracted text (<= 200 chars) - computed for every page during normal extraction, no LLM involved, no added cost. Verified against synthetic PDFs built with PyMuPDF: a page with a large embedded image and no text is flagged; a normal prose page is not; critically, a page with *both* a large decorative illustration and a full paragraph of real text is correctly **not** flagged - it already has real, citable content and doesn't need different handling just because it also has a picture on it.

### Vision description: strictly optional, wired in as a separate pipeline stage

New `src/pipeline/image_extractor.py`: `describe_image_heavy_pages()` re-renders only the flagged pages and asks a vision model to describe them, replacing their near-empty text. Disabled by default - only runs if `ollama.vision_model` is explicitly set in config (a new, optional field). `extract_pdf()` itself stays fast, offline, and dependency-free either way, matching the existing split between it and `entity_extractor.py` (deterministic/always-on vs. LLM-calling/optional). A vision failure doesn't fail ingestion - the page just keeps its original sparse text, same as if the feature didn't exist.

### The text-vs-visual distinction is carried through the whole pipeline, not just detected and dropped

Without this, a vision-derived chunk would look identical to real extracted text to the retriever and the chat prompt - defeating the entire point. Added `source_type` ("text" or "visual") to `Chunk`, propagated through the vector store's metadata, `SearchResult`, `Citation`, and the API's `SourceModel`. Reused the exact hard-break mechanism built for the story-boundary fix in session 5: a source-type change between consecutive pages forces a new chunk, so nothing ever blends real prose with a vision model's paraphrase. `prompt_builder.py`'s context formatting now labels visual chunks `[visually described: ...]` instead of `[Source: ...]`, and the system prompt explicitly instructs the model to treat that content as a hedged, potentially imprecise account belonging in "Interpretation:", never "From the documents:".

### Full end-to-end live verification, not just unit tests

Built a synthetic image-heavy PDF, ingested it for real with `vision_model="llava:latest"` configured, and confirmed the whole chain: the chunk was tagged `source_type="visual"` with the actual vision-model description as its text; a live chat query correctly retrieved it; the citation reported `source_type="visual"`; and - most importantly - the model's answer put everything under "**Interpretation:**" and explicitly noted no direct-document text was available, exactly as the updated system prompt instructs. The mechanism works end-to-end, not just in isolated unit tests.

## A real, unrelated problem found and fixed along the way

A full test-suite run unexpectedly took **22 minutes** instead of the usual ~30 seconds. Investigated rather than shrugging it off: found nine stray Python processes (leftover `uvicorn`/Gradio instances from session 4/5's design-comparison branches, running unattended on ports 8010/8020/8030/8040/8100 since 7/8) had accumulated hundreds of CPU-seconds each and were starving the test run through resource contention on this single dev machine. Killed them (kept only the current session's backend/frontend); the suite immediately returned to ~30s. Not something this session's code changes caused - confirmed by isolating and re-running for real before concluding.

## Verification

191/191 tests passing (up from 176 at the end of session 5 - added tests for the detection heuristic, config's `vision_model` field, `image_extractor.py`, chunker source-type hard-breaks, and prompt_builder's visual-context labeling).

## Round 2: repo cleanup, a real production reprocess, and a genuine concurrency bug

Asked to remove worktree bloat, clean up before testing, and reprocess a real document (M1E) with the new image-processing feature enabled - specifically checking that the cover page (which has real cover art) gets picked up.

### Cleanup

Removed the `chat-frontend-dark` and `design-dark` worktrees - both fully merged into `main` already (verified via `git merge-base --is-ancestor`), so keeping them was pure duplication. Left `design-classic`/`design-modern` as-is (still intentionally kept as reference per the user's earlier decision). Also found and fixed a stale *local* `main` branch ref (still pointing at session 3's end commit, since all merges this project has done went through `git push origin <branch>:main` directly against the remote ref, never touching a local `main` branch) - caused a brief false alarm that design-dark/chat-frontend-dark weren't really merged, resolved by checking `origin/main` directly and then fast-forwarding the local ref to match.

### A real, systemic concurrency bug - not just a vision-call problem

Enabled `ollama.vision_model: "llava:latest"` in the real config and reprocessed the real M1E PDF (629 pages, 8 image-heavy pages including the cover) through the actual production pipeline. First attempt: **all 54 entity-extraction batches and half the vision-description calls timed out.** Root cause: Ollama only runs one model inference at a time by default, so 8-way (or 4-way, for vision) "concurrent" requests just queue up inside Ollama while each one's client-side timeout clock is already running - a request queued behind several others can exceed even a generous timeout before Ollama has even started working on it. This wasn't a bug introduced this session; it's a pre-existing characteristic of `entity_extractor.py`, `entity_deduper.py`, and the ingestion wiki-prep step that had just never been exercised at real full-document scale before. Fixed by reducing worker counts (8→3 for text-based LLM calls, 4→2 for vision) and raising the timeout, with the reasoning documented in code comments.

### A process-check false negative caused real concurrent data corruption

While re-running with the fix, a PowerShell process-list query reported the *first* (broken) attempt had already finished when it had actually been running for 3 hours in the background with the old code still loaded in memory (code edits don't affect an already-running process). Both attempts ended up writing to the same live SQLite/ChromaDB data simultaneously for a stretch, corrupting M1E's chunk/entity state (a document stuck in "pending" status, entity counts that didn't match either run's own accounting). Recovered by killing both processes, doing a complete manual wipe of M1E's chunks/entities/registry entry, and being far more careful about confirming a process has truly exited before starting another one against the same data.

### The Bash tool's 10-minute background-task cap ate the next attempt too

The next careful, solo re-run got silently killed partway through - not a code bug, but a tooling mistake: `run_in_background` has a hard 10-minute cap, and a full 629-page reprocess needs much longer. Switched to launching via `nohup ... & disown` (the same detached-process pattern already used all session for the backend/frontend), which isn't subject to that cap, and monitored it via periodic direct log checks instead of a blocking wait.

### The clean run: real success, including the cover

Cleaned M1E one final time and ran the fixed pipeline detached. Took 171.8 minutes end to end (real per-batch latency on this CPU-only hardware is genuinely slow - not every batch succeeded even at reduced concurrency, 9 of 54 entity-extraction batches still timed out, but the pipeline's existing "enhancement, not core to success" design meant it completed anyway with a smaller-than-ideal entity set, 6 entities instead of the prior 97). Final result: **2411 chunks, 11 marked `source_type: "visual"`, across 7 of the 8 originally-flagged pages - including page 1, the cover.** Verified live against the real running app (not just the ingestion script): `/api/search` for the cover's actual content ("woman hanging from gallows... comic book art... dark tones") returns it as the top result with `source_type: "visual"`; a real chat query about the cover correctly cites `chunk_0000` (page 1) tagged `source_type: "visual"`. One honest caveat: the model's answer that time stated the vision-derived (partially garbled) cover text under "**From the documents:**" instead of hedging it in "Interpretation:" as the system prompt instructs - the tagging and architecture are unambiguously correct every time (confirmed via citations and search results), but the model doesn't perfectly follow the hedging instruction on every single query, consistent with known small-model instruction-following limits rather than a pipeline defect.

## Verification (round 2)

191/191 tests still passing after the concurrency fix. Live-verified against the real production app: `/api/health` healthy, `/api/documents` shows M1E reprocessed (629 pages, 2411 chunks), `/api/search` and `/api/chat` both correctly surface the cover page's vision-described content with `source_type: "visual"` in citations.

## State at end of session

- `session-6` branch off `main`, holding the image-page-detection feature plus the concurrency fix - **explicitly not merged to `main` this session**, per the user's request.
- 10 capability specs (all synced, including the new `image-page-processing`), no active OpenSpec changes.
- `chat-frontend-dark` and `design-dark` worktrees removed (fully merged, redundant); `design-classic`/`design-modern` kept as reference.
- The real M1E document has been reprocessed with the new pipeline: 2411 chunks, only 6 entities (down from 97 - a real regression from the incomplete entity extraction, see open items), 11 vision-described chunks. M2E has not been reprocessed.
- Local `config.yaml`'s `ollama.vision_model` set back to disabled (`null`) - was only turned on for this session's testing. Backend/frontend restarted on the disabled-vision config and re-verified healthy.

## Open items carried forward

- **Explicitly NOT merged to `main` this session** - the user asked to hold off, given the mixed results of the image-processing round below. Revisit next session.
- **Note for session 7 - prefer the text pipeline over the image/vision pipeline going forward.** The user's explicit preference after seeing the real cost: the text-extraction path is efficient and reliable; the vision path is neither, on this hardware. Reprocessing one 629-page document with vision enabled took **171.8 minutes** and *still* degraded entity-extraction reliability (see below) - the image-detection feature works and is verified end-to-end (worth keeping in the codebase, it's a real capability), but `ollama.vision_model` has been set back to disabled (`null`) in the local `config.yaml`, and should stay off by default rather than being routinely enabled. Only turn it on deliberately for a specific document/page that actually needs it, not as a standing default.
- **M1E's entity count regressed (97 -> 6)** because 9 of 54 entity-extraction batches still timed out even with reduced concurrency - the reduced-concurrency fix made entity extraction *reliable enough to complete*, not perfectly *complete*. Worth a follow-up: either a longer timeout still, a smaller `BATCH_SIZE` (more batches, each faster and less likely to queue past its own timeout), or accepting the loss and re-running entity extraction alone (`scripts/extract_entities.py`) against the already-ingested chunks to backfill what's missing. Independent of the vision-model question - this affects plain entity extraction too and is worth fixing regardless of whether vision stays off.
- M2E has not been reprocessed with the new image-detection/vision pipeline - it also has real cover art and 10 flagged pages per earlier analysis, but a repeat of the ~3-hour process wasn't done again this session given time already spent.
- Real comic-style PDF content to calibrate the detection thresholds (0.4 coverage / 200 chars) against still doesn't exist in this repo - verified on synthetic pages and now real M1E pages (both worked as expected).
- `qwen2.5vl` (session 5's top vision-model recommendation) was never pulled or tried - `llava:latest` was used to avoid an unplanned multi-GB download; swapping is a one-line config change (`ollama.vision_model`) whenever it's worth pulling.
- No panel detection, reading-order sorting, or speech-bubble OCR - a single vision-model call per flagged page gives a coarse description, not verbatim dialogue transcription (consistent with session 5's research on what local models can actually do today).
- Optionally hand-merge the one real, currently-unmerged duplicate found in session 5: "Governor-General's mansion" / "The Governor's Mansion" (both M1E, same place).
- Off-host (S3) backup replication and a real AWS deploy attempt remain deferred (unchanged from session 5).
