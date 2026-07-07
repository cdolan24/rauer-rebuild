## 1. Streaming chat (backend)

- [x] 1.1 Add `OllamaClient.chat_stream(model, messages, temperature) -> Iterator[str]`: parses Ollama's newline-delimited JSON streaming response, yields content fragments
- [x] 1.2 Add `num_predict` (generation length cap) and `keep_alive` options to `OllamaClient.chat`/`chat_stream`, config-driven with sensible defaults
- [x] 1.3 Add `ChatEngine.ask_stream(conversation_id, question) -> Iterator[...]`: same retrieval/prompt-building as `ask()`, yields text fragments then a final citations payload; stores the accumulated full answer in conversation history same as non-streaming
- [x] 1.4 Add `POST /api/chat/stream` (SSE) in `src/api/routes/chat.py`; leave `POST /api/chat` unchanged
- [x] 1.5 Unit/integration tests: streaming yields expected fragments + final citations; no-relevant-content case streams the fallback message as a single event; existing non-streaming endpoint behavior unchanged

## 2. Streaming chat (frontend)

- [x] 2.1 Add `ApiClient.send_chat_stream(message, conversation_id) -> Iterator[dict]` using `httpx`'s streaming client
- [x] 2.2 Update `send_message` in `src/frontend/app.py` to consume the stream and progressively update the chatbot's last message as fragments arrive, keeping the existing "Thinking..." placeholder until the first fragment lands

## 3. Enter-to-send keybinding

- [x] 3.1 Give the message textbox and send button stable `elem_id`s
- [x] 3.2 Inject a keydown handler (via `gr.Blocks(head=...)`) so Enter submits and Shift+Enter inserts a newline
- [x] 3.3 Playwright check: Enter submits, Shift+Enter adds a newline without submitting

## 4. Citation display

- [x] 4.1 Replace the citations `gr.Dropdown` with a `gr.Radio` (button-style) group
- [x] 4.2 Humanize citation labels (shortened document name + page, not the raw document id)
- [x] 4.3 Update tests/verification for the new citation control

## 5. PDF document viewer

- [x] 5.1 Replace the `doc_viewer` Textbox with a `gr.HTML` iframe pointed at `/api/documents/{id}/pdf#page=N`
- [x] 5.2 Update `view_citation` and `view_selected_document` to build the iframe HTML instead of fetching processed text
- [x] 5.3 Remove the now-redundant separate "View original PDF" link
- [x] 5.4 Playwright/browser check: selecting a citation or a document shows the real PDF, at the right page for a citation

## 6. Wiki buttons

- [x] 6.1 Add button-style CSS to `src/wiki/templates/base.html`
- [x] 6.2 Apply the button class to entity/category links in `index.html` and `category.html`
- [x] 6.3 Test/verify wiki pages still render correctly with the new styling

## 7. Verify & ship

- [x] 7.1 Run full test suite once, confirm green
- [x] 7.2 Restart backend + frontend
- [x] 7.3 One tight Playwright pass covering everything new: streaming response appears incrementally, Enter/Shift+Enter behavior, citation buttons with humanized labels, PDF iframe viewer (both citation and document-selector paths), wiki buttons
- [ ] 7.4 Archive the OpenSpec change (sync specs first), commit and push
