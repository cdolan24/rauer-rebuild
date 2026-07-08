## 1. Conversation session isolation

- [x] 1.1 Change `conversation_id = gr.State(str(uuid.uuid4()))` to `gr.State(lambda: str(uuid.uuid4()))` in `src/frontend/app.py`
- [x] 1.2 Verify via Playwright: two independent browser contexts get distinct conversation ids (checked via the backend's query log, since the conversation_id is used server-side, not sent as a browser-visible request)

## 2. Faster model investigation (documented, no code ships)

- [x] 2.1 Benchmark `llama3.2:1b` against `llama3.2:latest` using the real retriever's actual output for two real questions
- [x] 2.2 Decision: reject - real hallucination observed on real context both times; document in design.md, no config change

## 3. Entity deduplication

- [x] 3.1 Add `EntityStore.merge_entities(keep_id, merge_ids)`: reassign mentions, delete duplicate rows, clear the surviving entity's cached summary
- [x] 3.2 Create `src/pipeline/entity_deduper.py`: `find_duplicate_groups(entities, ollama_client, chat_model)` - groups by type, one LLM call per type, validates every returned id against the actual entity-id set, rejects self-referential/malformed groups
- [x] 3.3 Unit/integration tests: merge reassigns mentions and deletes duplicates; parser rejects hallucinated ids, self-merges, and ids claimed by more than one group
- [x] 3.4 Create `scripts/dedupe_entities.py` with `--dry-run` mode
- [x] 3.5 Back up the entity database; run `--dry-run` and review proposed merge groups before applying anything
- [x] 3.6 Apply the reviewed merges; spot-check the wiki (e.g. "Molly Squidpiddge" variants, "Samael" variants) no longer show as separate entities

## 4. Verify & ship

- [ ] 4.1 Run full test suite, confirm green
- [ ] 4.2 Restart backend + frontend
- [ ] 4.3 Playwright pass covering the merged entity data in the live wiki
- [ ] 4.4 Archive the OpenSpec change (sync specs first), commit and push to `session-4`
