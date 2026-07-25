## Context

Live-tested both locally-pulled vision models (`llava:latest`, `llama3.2-vision:latest`) against a real rendered page via Ollama's `/api/chat` endpoint on this CPU-only dev machine: `llava` completed in 93s but hallucinated details on a plain text page ("a mobile phone screen"); `llama3.2-vision` didn't finish within 120s. This matches session 5's research - local vision models are usable for coarse description today, not verbatim-trustworthy, and meaningfully slower without a GPU (the same conclusion already reached for the text model). Ollama's chat API already accepts an `"images"` field per message (base64-encoded), which the existing `OllamaClient.chat()` passes through unmodified since it forwards `messages` verbatim into the request payload - no client changes needed to send an image.

No real comic-style PDF exists in `data/` to calibrate a detection heuristic against - M1E/M2E are both prose anthologies. The heuristic's thresholds are therefore reasoned defaults, verified against synthetic test pages (a real embedded image with no text vs. real prose), not tuned against real comic data.

## Goals / Non-Goals

**Goals:**
- Detect an image-heavy page automatically and for free (no LLM call) during normal PDF extraction.
- Make vision-model description an explicit opt-in (`ollama.vision_model` config), never active by default.
- Carry the text-vs-visual distinction through the whole pipeline so a chat answer can treat visually-described content with appropriately lower trust, rather than silently blending it with directly-extracted prose.

**Non-Goals:**
- Not doing panel detection, reading-order sorting, or speech-bubble OCR (the multi-stage approach real comic-transcription research uses) - out of scope for this pass. A single vision-model call per flagged page produces a coarse description, not verbatim dialogue transcription, and the design doesn't pretend otherwise.
- Not tuning the detection thresholds against real comic data (none exists in this repo) - documented as reasoned defaults, verified on synthetic pages.
- Not re-ingesting the existing M1E/M2E data as part of this change - neither document has image-heavy pages by the heuristic (both are prose), so there's nothing to re-process.
- Not pulling a new vision model (e.g. `qwen2.5vl`, session 5's top recommendation) - prototyping with the already-pulled `llava:latest` to avoid an unplanned multi-GB download; swapping models later is a one-line config change.

## Decisions

**Detection lives in `pdf_extractor.py` as a pure, always-on heuristic; the vision-model call lives in a separate, optional module.** Mirrors the existing split between `pdf_extractor.py` (fast, offline, always runs) and `entity_extractor.py` (LLM-calling, optional, wired in only when configured). `extract_pdf()` stays fast and dependency-free; nothing changes for a deployment that never sets `vision_model`.

**Heuristic: image coverage ratio >= 0.4 AND extracted text <= 200 characters.** A page with a large decorative illustration *and* a full column of prose text is not what needs a different pipeline - it already has real, citable text. Requiring both low text and high image coverage targets pages where the visual content actually carries the meaning.

**A page's origin (`text` vs `visual`) is a hard chunk-boundary, reusing the exact mechanism built for story-boundary detection.** A chunk should never blend a paragraph of real prose with a vision-model's paraphrase of a different page - same reasoning as not blending two different stories into one chunk.

**Vision model is a separate config field (`ollama.vision_model`), defaulting to unset/disabled, not reused from `ollama.chat_model`.** The user was explicit: this must not become the default model for anything. An empty/missing config value means the whole feature is inert - image-heavy pages just keep whatever sparse text `get_text()` produced, tagged accordingly, same as today's behavior for such a page.

**Citations carry `source_type` all the way to the prompt and the API response, not just internally.** Without this, a vision-derived chunk looks identical to real extracted text to the retriever and the chat prompt - defeating the entire point of flagging it. The system prompt is updated to tell the model to treat `source_type: visual` context as a rough visual description, appropriately hedged, rather than a directly quotable fact.

## Risks / Trade-offs

- [Risk] The 0.4/200-char thresholds are unvalidated against real comic content. → Verified against synthetic pages (a real embedded image with no text; a real prose paragraph) proving the heuristic distinguishes the two cases it's designed for; flagged as needing recalibration once real comic-style PDFs are ingested.
- [Risk] `llava`'s description quality was poor in the one live test run (hallucinated a "mobile phone screen" for a plain text page). → Exactly why this is opt-in and why the prompt/system-message work treats this content as lower-trust, not a source of fact on par with real text.
- [Risk] Vision calls are slow (93s+ per page on this hardware) - enabling this on a large image-heavy document could make ingestion take a very long time. → Consistent with the project's existing stance (session 4/5) that this app's local-LLM latency profile requires a GPU for real production use; not a new problem this change introduces.
