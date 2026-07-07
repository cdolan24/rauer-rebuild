# Session 2

**Branch:** `session-2` (merged into `main`)
**OpenSpec changes:** `entity-wiki-and-citations` (archived `2026-07-07-entity-wiki-and-citations`)

Consolidates the two granular logs from this session (`2026-07-07-entity-wiki-and-citations.md`, `2026-07-07-efficiency-and-branch-split.md`), which this file replaces.

## What shipped

- **Entity extraction** (`src/pipeline/entity_extractor.py`, `src/database/entity_store.py`): batched (not per-chunk) LLM calls tag chunks with named entities (character/location/faction/item); mention indexing is plain substring matching (no extra LLM cost). Ran against the real corpus: M1E 99 entities/3635 mentions, M2E 34 entities/1526 mentions (133/5161 total).
- **Entity-aware retrieval boost** (`src/rag/retriever.py`): a query naming a known entity gets matching chunks boosted (+0.05 cosine score) over a widened candidate pool. Verified on real data: 0.7143→0.7643 etc. for a "Who is Lady Justice?" query.
- **Wiki** (`src/wiki/`): FastAPI + Jinja2, served from the backend (port 8000, not the Gradio frontend) - category index, per-entity pages with an LLM-written summary and "Mentioned In" citations. Linked from the main chat page.
- **PDF-native citations**: `GET /api/documents/{id}/pdf` + `#page=N` convention, used by chat citations and wiki pages alike.
- **Entity extraction concurrency fix**: the processor ran every batch strictly sequentially (the actual reason M1E+M2E took most of a day combined) - fixed with a `ThreadPoolExecutor` (same pattern `embeddings.py` already used), ~4x measured speedup on a real subset.
- **Test suite pass**: cut two low-value tests (a one-line early-return check, a test of ChromaDB's own filtering rather than our logic); kept everything else, including the tests that had directly caught real bugs this project (cosine scoring, Ollama timeouts).

## Two real failures hit and fixed along the way

1. **Mid-run extraction crash**: a batch's LLM call timed out (even at the already-raised 180s backend timeout), and since the code did all-batches-then-all-mentions, the whole run's mention indexing was lost, not just the failed batch. Fixed with per-batch try/except (log and continue), covered by a regression test.
2. **Bash/PowerShell 10-minute tool cap**: a multi-hour extraction job can't run as one tool call, even backgrounded. Fixed by launching as a fully detached OS process (`nohup ... & disown`, same pattern as the backend/frontend servers) and polling for completion via `Get-Process` instead of a blocking wait.

## Branch reorg (done at user's explicit request)

Entity-wiki-and-citations had originally been pushed straight to `main`. Un-did that cleanly: reverted the two commits on `main` via `git revert` (no force-push, no rewritten history - verified via test count matching session-1 exactly, 68/68) and moved all of session 2's work to a new `session-2` branch. Later, per further instruction, merged `session-2` back into `main` - hit the classic "revert-then-remerge" git gotcha (reverting a commit and then merging the branch that still has it makes git silently drop the reverted files again, since the merge-base sees them as "deleted on main, unchanged on the other side"). Fixed by reverting the revert commits first (restoring `main` to the merge-base content), then merging cleanly. Verified with `git diff main session-2` returning empty before pushing.

## State at end of session

- `main`: `089fdb3` (all of session 2's work merged in, pushed).
- `session-2` branch: still exists at `07faa19`, now fully absorbed into `main`.
- 97/97 tests, 7 capability specs, no active OpenSpec changes.

## Open items carried into session 3

- `TEST.pdf` duplicate of M1E still unprocessed by design.
- Cross-document entity de-duplication out of scope (same-name entities exist as separate rows per document).
- Chunking can straddle story boundaries in the multi-story anthology (seen directly on M1E pages 31-32).
- Entity extraction occasionally tags non-diegetic names (book credits) as "characters" - a known LLM-extraction limitation, not filtered.
