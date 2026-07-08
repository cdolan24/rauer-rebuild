## Context

**Shared conversation ID**: `src/frontend/app.py` had `conversation_id = gr.State(str(uuid.uuid4()))`. `gr.State`'s `value` argument is evaluated once, at the time the `gr.Blocks` is constructed (module load), not per session - Gradio's own docs confirm the fix: "If a callable is provided, the function will be called whenever the app loads." Verified live: two independent Playwright browser contexts each submitting a message showed identical `conversation_id`s in the backend's query log before the fix, and distinct ones after.

**Entity fragmentation**: visible directly in the Characters category page - "Molly Squidpiddge" / "Molly Squidpiddge (again)" / "Molly-girl" and "Samael" / "Samael Hopkins" / "Deputy Samael Hopkins" are each really one character, split across separate rows because the extraction pipeline only dedupes by exact name match within a single document's extraction call, never across name variants or across documents.

**Faster model, investigated and rejected**: `llama3.2:1b` was pulled and benchmarked against the current `llama3.2:latest` (3B) using the actual live retriever's real output for two real questions ("Who is Lady Justice?", "What is the Ortega family known for?"), not synthetic filler text. Prompt evaluation was ~3x faster (6-7s vs 18-23s) and generation somewhat faster too, but the 1B model's answers showed real hallucination on both real questions: confusing Perdita's siblings with monster types ("Sonnia (a Gremlin)", "Santiago (a Peacebringer)") and inventing plausible-sounding but wrong specifics. The 3B model stayed coherent and grounded on the same real context both times. Given the project's core requirement is grounded, non-fabricated answers, this isn't a trade worth making - no model change ships.

## Goals / Non-Goals

**Goals:**
- Each browser session gets its own conversation history.
- Merge entities that are genuinely the same underlying thing under different name variants, using only already-extracted name/description (no source re-reading, matching the reclassification pass's approach from the previous change).

**Non-Goals:**
- Not re-evaluating chat models further this round - the 1B investigation's conclusion (reject) is documented above, not re-litigated.
- Not attempting fully-automatic unattended merging - a `--dry-run` mode exists specifically because entity merging is inherently riskier than reclassification (wrongly merging two distinct entities loses information; the reclassification pass, by contrast, can be freely re-run since it can't destroy data).

## Decisions

1. **`gr.State(lambda: str(uuid.uuid4()))`** - the minimal fix; no architecture change needed, this is exactly the mechanism Gradio provides for this exact problem.

2. **Merge within type only, one LLM call per type, whole-list-at-once.** Entities are grouped by type first (merging a `location` with a `character` never makes sense), then each type's full entity list (id/name/description) is sent to the model in a single call asking for merge groups as `[{"keep_id": <id>, "merge_ids": [<id>, ...]}]`. At current scale (max 97 entities in the largest type, `character`) this comfortably fits in one prompt and preserves full cross-referencing within the type - sub-batching would risk missing duplicates that land in different batches (exactly the problem this is trying to solve for cross-document fragmentation, so it can't be sub-batched away). Response parsing validates every id against the actual entity-id set for that type-batch and rejects malformed or self-referential groups, since a hallucinated id would otherwise corrupt the database.

3. **A `keep_id` is chosen by the model** (told to pick whichever candidate has the most complete/informative description), rather than always keeping the lowest id or first-added row - since the goal is the best surviving record, not procedural simplicity.

4. **`EntityStore.merge_entities(keep_id, merge_ids)`**: reassigns all `entity_mentions` rows from the merged-away ids onto `keep_id`, deletes the merged-away entity rows, and clears `keep_id`'s cached summary (since its mention count/content just changed materially - the wiki will regenerate a fresh one on next view, same mechanism as any entity that's never had a summary cached).

5. **`--dry-run` mode on the script**, printing every proposed merge group before applying anything - given the real risk of an over-aggressive merge (unlike reclassification, a bad merge can't be trivially undone without restoring from backup), review-before-apply is the safer default workflow, and matches how the reclassification prompt itself needed real iteration before being trusted to run for real.

## Risks / Trade-offs

- [The model could merge two genuinely distinct entities that happen to share a similar name] → Mitigated by an explicitly conservative prompt (only merge on high confidence, e.g. clear name variants/aliases/coreference - not just similarity) and mandatory dry-run review before applying; DB backed up before the real run regardless.
- [Merging deletes rows - harder to undo than reclassification's plain type overwrite] → DB backup taken before running; `--dry-run` output reviewed first.
