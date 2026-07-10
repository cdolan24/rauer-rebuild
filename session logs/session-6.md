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

## State at end of session

- `session-6` branch off `main`, holding the image-page-detection feature; not yet merged to `main`.
- 10 capability specs (all synced, including the new `image-page-processing`), no active OpenSpec changes.
- Backend/frontend processes cleaned up to just the current session's pair.

## Open items carried forward

- Merge `session-6` into `main` when the user is ready.
- Real comic-style PDF content to calibrate the detection thresholds (0.4 coverage / 200 chars) against doesn't exist in this repo yet - verified on synthetic pages only.
- `qwen2.5vl` (session 5's top vision-model recommendation) was never pulled or tried - `llava:latest` was used to avoid an unplanned multi-GB download; swapping is a one-line config change (`ollama.vision_model`) whenever it's worth pulling.
- No panel detection, reading-order sorting, or speech-bubble OCR - a single vision-model call per flagged page gives a coarse description, not verbatim dialogue transcription (consistent with session 5's research on what local models can actually do today).
- Decide whether to re-ingest the live M1E/M2E data to pick up session 5's chunking-boundary and auto-dedup/summarize fixes (still pending from session 5 - neither document has image-heavy pages, so this session's feature doesn't add a new reason to re-ingest them).
- Optionally hand-merge the one real, currently-unmerged duplicate found in session 5: "Governor-General's mansion" / "The Governor's Mansion" (both M1E, same place).
- Off-host (S3) backup replication and a real AWS deploy attempt remain deferred (unchanged from session 5).
