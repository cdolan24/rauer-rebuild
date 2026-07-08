## 1. Wiki layout foundation

- [x] 1.1 Restructure `base.html` into a two-column layout: persistent left sidebar (category nav + search box) and a main content area, replacing the current single centered column
- [x] 1.2 Pass category counts to every wiki route (`wiki_index`, `wiki_category`, `wiki_entity`) so the sidebar can render on all three pages
- [x] 1.3 Add breadcrumb blocks to `category.html` and `entity.html` ("Wiki Home > {Category}" / "Wiki Home > {Category} > {Entity}")

## 2. Entity search

- [x] 2.1 Add a search input to the sidebar, with a small inline `<script>` that filters visible entity buttons on the index/category pages by name substring (case-insensitive), no backend call
- [x] 2.2 Verify filtering and clearing behave correctly via Playwright

## 3. Entity infobox

- [x] 3.1 In `wiki_entity` (`src/wiki/routes.py`), compute the distinct source documents from `mentions` and pass to the template alongside mention count
- [x] 3.2 Add an infobox block to `entity.html` showing type, mention count, and distinct source documents

## 4. PDF inline serving

- [x] 4.1 `FileResponse(..., content_disposition_type="inline")` on `GET /api/documents/{id}/pdf` (already applied)
- [x] 4.2 Regression test asserting `Content-Disposition` starts with `inline` (already added to `tests/integration/test_api.py`) - confirm still passing after other changes in this task list

## 5. Bounded conversation history

- [x] 5.1 Add `rag.max_history_turns` to config (default 3), `Config`/`load_config`
- [x] 5.2 `ChatEngine` accepts `max_history_turns`, truncates history passed to `build_messages` to the last N turns (both `ask()` and `ask_stream()`)
- [x] 5.3 Wire the config value through `src/api/main.py`
- [x] 5.4 Unit/integration tests: history beyond the cap is dropped, history within the cap is unaffected

## 6. Spec documentation (no code)

- [x] 6.1 Confirm the `rag-chat` "Multiple sources cited for one answer" scenario matches actual `ChatEngine` behavior (no code change expected - existing behavior already does this)

## 7. Verify & ship

- [x] 7.1 Run full test suite, confirm green
- [x] 7.2 Restart backend + frontend (session-3 dev instance, not the session-2 demo)
- [x] 7.3 Playwright pass: sidebar visible on all three wiki page types, search filters correctly, breadcrumbs link correctly, infobox renders, PDF opens inline (not download), conversation history truncation doesn't break multi-turn chat
- [ ] 7.4 Archive the OpenSpec change (sync specs first), commit and push to `session-3`
