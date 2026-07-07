## Context

Chat responses are generated in one blocking call, then returned to the user all at once - for a 40-90s+ generation, that's 40-90s of a frozen-looking UI (the "Thinking..." placeholder from the MVP helps, but it's still a single long wait). Separately, several UI details didn't get real design attention during the MVP build: keybinding, citation display, the document viewer showing the AI's plain-text extract instead of the source PDF, and the wiki's bare links.

## Goals / Non-Goals

**Goals:**
- Make the chat feel responsive: first content appears quickly, then fills in, instead of one long wait.
- Bound worst-case response time and avoid avoidable cold-start delay.
- Fix the four concrete UI complaints without redesigning the whole app.

**Non-Goals:**
- Not changing the model, hardware, or retrieval defaults (top_k, min_score) - those are separate, already-tunable levers, and changing them now would confound whether a speed change came from streaming or from answering with less context.
- Not building a full custom PDF viewer/renderer - reusing the browser's native PDF viewer via an iframe, same as the existing PDF-citation-link mechanism.
- Not a wiki visual redesign beyond turning links into buttons - no new layout/nav structure.

## Decisions

**1. Streaming via Server-Sent Events on a new `/api/chat/stream` endpoint, not a rewrite of `/api/chat`.**
The existing `POST /api/chat` contract (used by search/tests/any future non-streaming caller) stays exactly as-is. A new endpoint streams `text/event-stream` chunks: one event per generated token/fragment, then a final event carrying the citations (known up front from retrieval, but sent last so the frontend can show accumulating text immediately without waiting on them). `ChatEngine` gets a new `ask_stream()` generator alongside the existing `ask()`; both share the same retrieval/prompt-building code, only the generation call differs (`OllamaClient.chat()` vs. a new `OllamaClient.chat_stream()` that parses Ollama's own newline-delimited-JSON streaming response).

**2. Frontend consumes the stream via `httpx`'s streaming client, feeding Gradio's existing generator-based chat callback.**
`send_message` in `app.py` is already a generator (used for the "Thinking..." placeholder) - extending it to yield progressively-updated partial text as stream chunks arrive is a natural fit, no new UI framework needed.

**3. Bound generation length via Ollama's `num_predict` option; keep the model warm via `keep_alive`.**
Both are options already exposed by Ollama's API, just never set. `num_predict` caps worst-case latency from an unusually long/rambling generation. `keep_alive` (set generously, e.g. 30 minutes) avoids the model being unloaded between spaced-out user questions, which would otherwise reintroduce a cold-start delay on the next request regardless of streaming.

**4. Enter-to-send via a small injected JS keydown handler, not a different Gradio component.**
Gradio's multi-line `Textbox` has no built-in "Enter submits, Shift+Enter newlines" behavior - that's standard chat-app convention but not a native option. Simplest fix: give the textbox and send button stable `elem_id`s and inject a short script (via `gr.Blocks(head=...)`) that intercepts `keydown` on the textbox - Enter without Shift prevents the default newline and clicks the send button; Shift+Enter is left alone (default textarea behavior already inserts a newline).

**5. Citations become a `gr.Radio` (rendered as selectable pill buttons) with humanized labels, not a `gr.Dropdown`.**
A dropdown hides all the options behind a click with no visual affordance that "there's something interesting here." A `Radio` group renders every citation as a visible clickable button up front. Labels get shortened (drop the `_DRAFT_5.17.2023` suffix noise, keep document short-name + page) since the full document id is redundant once there are only two ingested documents to distinguish.

**6. Document viewer becomes an embedded PDF iframe pointed at the existing `/pdf#page=N` endpoint, replacing the plain-text panel entirely.**
The processed text/`_extract_page_range` machinery stays exactly as it is for what it's actually for (AI retrieval, wiki entity summaries) - this only changes what a human sees when they select a citation or a document: the real, formatted PDF page instead of a plain-text dump. Removes the now-redundant separate "View original PDF" link introduced in `entity-wiki-and-citations`, since the whole panel *is* the PDF now.

**7. Wiki buttons: CSS-only change to existing templates.**
`<a>` tags for entities/categories get a `.entity-button`/`.category-button` class (padding, background, border-radius, hover state) - no template restructuring, no new routes.

## Risks / Trade-offs

- **[Risk]** Streaming adds a second code path (streaming vs. non-streaming chat) that could drift out of sync → **Mitigation**: both share the same retrieval/prompt-building functions; only the final Ollama call and response shape differ.
- **[Risk]** `num_predict` cap could cut off a legitimately long answer → **Mitigation**: set generously (not aggressively low); this bounds pathological cases, not normal answers.
- **[Risk]** Embedding a cross-origin PDF (backend on :8000) in an iframe on the frontend (:7860) - could be blocked by a browser/CSP policy → **Mitigation**: FastAPI doesn't set restrictive frame headers by default; verify directly in-browser as part of this change's verification.
- **[Risk]** Enter-to-send JS could conflict with Gradio's own event wiring or IME (composition) input for non-Latin scripts → **Mitigation**: scope the keydown handler narrowly (check `e.isComposing`/`keyCode` guards), verify Enter/Shift+Enter both behave correctly in-browser.
