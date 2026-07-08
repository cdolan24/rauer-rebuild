# Session 3

**Branch:** `session-3` (not yet merged to `main`)
**OpenSpec changes:** `chat-speed-and-ui-polish` (archived `2026-07-07-chat-speed-and-ui-polish`), `wiki-redesign-and-chat-perf` (archived `2026-07-07-wiki-redesign-and-chat-perf`)

## What shipped

- **Streaming chat responses**: `OllamaClient.chat_stream()` parses Ollama's newline-delimited streaming JSON; `ChatEngine.ask_stream()` yields answer fragments then a final `ChatResponse`; `POST /api/chat/stream` (SSE, `src/api/routes/chat.py`) exposes it without touching the existing non-streaming `POST /api/chat`. Frontend (`ApiClient.send_chat_stream`, `send_message` in `src/frontend/app.py`) consumes the stream and grows the chat bubble token-by-token, replacing the old "wait ~40-90s for one big reply" experience.
- **Generation tuning**: `num_predict` (512, caps runaway generations) and `keep_alive` (30m, avoids repeated model-load latency) are now config-driven (`config.yaml` → `Config.ollama` → `ChatEngine` → `OllamaClient`), not hardcoded.
- **Enter-to-send / Shift+Enter-newline**: injected via `gr.Blocks(head=...)` JS against stable `elem_id`s (`message_box`, `send_btn`).
- **Citation buttons**: `gr.Radio` (button-styled) replacing `gr.Dropdown`, with humanized labels (`"Malifauxstories M2E Draft..." (p. 501)` instead of the raw document id).
- **PDF document viewer**: citation/document selection now embeds the real PDF via `<iframe src=".../pdf#page=N">` (`_pdf_viewer_html`), replacing the old plain-processed-text `Textbox` + separate "View original PDF" link. Processed text stays available server-side (`/api/documents/{id}/content`) for the AI's own retrieval grounding; only the human-facing viewer changed. Removed the now-dead `ApiClient.get_document_content` and `_extract_page_range` from the frontend.
- **Wiki buttons**: category and entity links in `index.html`/`category.html` are now `.wiki-btn` pill buttons (CSS added to `base.html`) instead of plain text links.

## A real bug hit and fixed during Playwright verification

Enter-to-send worked immediately, but Shift+Enter didn't - the whole textbox emptied instead of getting a newline. Root cause took three rounds of live DOM debugging to pin down:

1. First guess (wrong): needed `stopImmediatePropagation()` instead of `stopPropagation()` in case Gradio had a sibling `keydown` listener on the same node. Instrumenting `addEventListener` itself (monkey-patched before Gradio's bundle loaded) proved there was no such sibling listener - `keydown` on `document` in capture phase was ours alone.
2. Actual cause: Gradio's multiline Textbox doesn't watch `keydown` for its submit-on-Enter behavior at all - it reacts to the native `input` event the browser fires with `inputType: "insertLineBreak"` once Enter's default newline action completes. Letting the browser's default action happen for Shift+Enter (which is what "just don't preventDefault" does) was exactly the event Gradio was submitting on, regardless of the Shift key (`InputEvent` doesn't carry modifier-key state the way `KeyboardEvent` does).
3. Fix: `preventDefault()` the native newline entirely for *both* Enter and Shift+Enter, then for Shift+Enter manually splice `\n` into the textarea's value and dispatch a synthetic `input` event tagged `inputType: "insertText"` - a normal edit Svelte's binding accepts without tripping Gradio's `insertLineBreak`-specific submit check.

Backend streaming itself needed no such fighting - `OllamaClient.chat_stream`/`ChatEngine.ask_stream`/the SSE route were covered by unit and integration tests from the start and worked first try.

## Verification

- 106/106 tests passing (up from 97 at the end of session 2 - added streaming unit/integration tests, no tests removed this session).
- Backend + frontend restarted fresh; live Playwright pass against a real question ("Who is Lady Justice?", real Ollama, real ChromaDB data) confirmed all 9 checks: Shift+Enter inserts a newline without submitting, Enter submits and clears the box, the answer visibly streams in incrementally (16 distinct growing snapshots observed) rather than appearing as one chunk, citation buttons render with humanized labels, selecting a citation or a document opens the real PDF in an iframe at the right page, and the wiki's category/entity links render as styled buttons (19 confirmed on the index page).

## State at end of session

- `session-3` branch (not merged to `main` yet - stays isolated per this project's established session-branching convention until explicitly asked to merge).
- 108/108 tests, 7 capability specs (all synced), no active OpenSpec changes.
- Session-2 (`main`) demo running at ports 8000/7860 via the `../rauer-rebuild-session2-demo` worktree, untouched by this session's work.
- Session-3 dev build running at ports 8001/7861 (config `config.yaml`'s ports, launched via an alternate-port config for side-by-side testing against the demo).

## Round 2: `wiki-redesign-and-chat-perf`

After the first round shipped, live user feedback surfaced three more things: chat "thinking" time was still long, the wiki's flat button-list didn't hold up navigationally, and PDFs were downloading instead of opening inline in the viewer just built.

### Diagnosing chat speed with real numbers, not guesses

Measured directly against the real Ollama install rather than assuming: `ollama ps` confirmed **100% CPU, no GPU**. A minimal 33-token prompt took 0.82s of `prompt_eval_duration`; a realistic RAG prompt (5 retrieved chunks + system prompt, ~1020 tokens) took **26.98s of prompt evaluation alone**, out of 38.44s total (`eval_duration` - actual generation - was 11.36s for 156 tokens). Streaming (round 1) can't help this: it only makes generation feel responsive once tokens start, and this delay is entirely *before* the first token.

The direct fix (smaller `top_k`/`chunk_size`) trades straight against the richer, multi-citation answers the user explicitly said they wanted to keep - so that lever was deliberately left alone (documented as an open question, not applied unilaterally). Instead: **bounded conversation history** (`rag.max_history_turns`, default 3) - `ChatEngine` now resends only the last N turns instead of the full, ever-growing history. This costs nothing on a fresh question or short conversation and stops the compounding growth on long ones. Also documented, as an explicit spec requirement rather than an implicit side effect, that citing multiple sources for one answer is intentional behavior worth protecting from future "just make it faster" changes.

### Wiki redesign (Fandom/Wikipedia-inspired)

- Persistent sidebar (`base.html`) with category nav + counts, visible on all three wiki page types now (`wiki_index`/`wiki_category`/`wiki_entity` all pass `category_counts`).
- Client-side entity search: a single delegated `input` listener filtering `.entity-grid`/`.entity-list` items by name substring - no backend endpoint, appropriate at the current ~133-entity scale.
- Breadcrumbs (`Wiki Home > Category > Entity`) on category/entity pages.
- Entity infobox (type, mention count, distinct source documents) on entity pages, computed in `wiki_entity` from the existing `mentions` list.

### Two more real bugs found and fixed

1. **PDF downloads instead of opening inline**: `FileResponse(..., filename=...)` defaults to `Content-Disposition: attachment` in Starlette. One-line fix: `content_disposition_type="inline"`.
2. **Frontend silently ignored `BUDDHARAUER_CONFIG`**: `src/frontend/app.py`'s `main()` called `load_config()` with no arguments (hardcoded default `"config.yaml"`), never calling `get_config_path()` the way `src/api/main.py` does. Found while trying to stand up a second dev instance on alternate ports for testing without disturbing the live demo - the frontend kept binding to the demo's port instead of the one in the alternate config. Fixed to match the backend's pattern.

### Demo/dev isolation this round

Ran the session-2 (`main`) build as a live demo throughout, via a separate `git worktree` at `../rauer-rebuild-session2-demo` pointed at the same underlying `vector_db`/`data_storage`/`processed` data (absolute paths in its `config.yaml`) so it shows real ingested content without re-ingesting anything. All `session-3` development and verification happened in the primary checkout on alternate ports (8001/7861), so the demo was never interrupted.

### Verification

108/108 tests passing (up from 106 - added history-bounding tests, PDF-disposition regression test). Live Playwright pass against the session-3 dev instance confirmed: sidebar on all three wiki page types, search narrows results and clearing restores them, breadcrumbs link correctly, infobox renders type/mentions/source-documents, and the PDF endpoint returns `Content-Disposition: inline`.

## Open items carried forward

- The `conversation_id = gr.State(str(uuid.uuid4()))` default in `src/frontend/app.py` is evaluated once at app-build time, not per browser session - every visitor currently shares one conversation history. Still not fixed (out of scope both rounds this session), worth doing before multi-user use.
- Whether to reduce `top_k`/`chunk_size` (a real further speed lever) or switch to a smaller/faster/GPU-backed model is an open, deliberately-deferred decision - it trades against answer richness, which the user confirmed they want to keep.
- Client-side wiki search doesn't scale indefinitely - revisit with a backend search index if entity count grows an order of magnitude.
- Open items from session 2 (`TEST.pdf` duplicate, cross-document entity de-duplication, chunking across story boundaries, occasional non-diegetic entity tagging) remain untouched.
