## Why

Two separate complaints from using the real app: chat responses feel slow (the user waits for the entire answer to generate before seeing anything), and several UI details are unintuitive - Enter doesn't send the message, the citation dropdown is opaque, the document viewer shows the AI's plain-text extract instead of the real PDF, and the wiki reads as a wall of links rather than something clickable/browsable.

## What Changes

- Stream chat responses token-by-token instead of waiting for the full answer (biggest lever on *perceived* speed - total generation time is mostly fixed by the local model/hardware, but time-to-first-token and the "am I stuck" wait matter more to a user).
- Bound worst-case generation length and keep the Ollama model warm between requests (avoid model-reload cold starts).
- Frontend: Enter sends the message, Shift+Enter inserts a newline (chat-app convention).
- Frontend: citation list restyled as clickable pill buttons with human-readable labels, instead of a plain dropdown of raw document ids.
- Frontend: the document viewer now embeds the actual PDF (via the existing `/pdf#page=N` endpoint) instead of the plain-text extract - the processed text stays in use internally for the AI (retrieval, wiki summaries) but is no longer shown to a human.
- Wiki: entity/category links restyled as buttons/cards instead of plain inline text links.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `rag-chat`: chat responses are now streamed; generation length is bounded.
- `chat-api`: new streaming chat endpoint; existing non-streaming endpoint kept for other callers (search, etc. are unaffected).
- `chat-frontend`: Enter/Shift+Enter behavior, citation display, and document viewer (PDF instead of plain text) all change.
- `wiki`: entity/category listings are styled as buttons, not plain links.

## Impact

- **Code**: `src/utils/ollama_client.py` (streaming + keep_alive), `src/rag/chat_engine.py` (streaming variant), `src/api/routes/chat.py` (new SSE endpoint), `src/frontend/api_client.py` + `src/frontend/app.py` (streaming consumption, keybinding JS, citation/viewer rework), `src/wiki/templates/*.html` (button styling).
- **No change** to `/api/chat`'s existing non-streaming contract - it stays as-is for any caller that doesn't need streaming.
- **Non-goals**: no model swap, no change to retrieval/top_k defaults (those remain separate, already-configurable levers), no cross-document entity work.
