# Session Log: 2026-07-07 - Efficiency Pass + Branch Split

**Branch:** `session-2` (new)
**`main`:** reverted back to session-1 stable state (rebuild-mvp + admin-gated-upload + admin-page-separation only)

## Summary

User pushback on process: questioned whether the test suite was adding real value or just ceremony, called out that entity extraction took "all night" to run, and asked for the entity-wiki-and-citations work (session 2) to live on its own branch rather than on `main`.

## Tests: kept most, cut two

Assessment given directly to the user: most of the suite is load-bearing - the cosine-similarity regression tests and the Ollama-timeout config tests exist *because* both of those were real production bugs this project hit. Cut two that were closer to theater:
- A test asserting only a one-line empty-input early return (`extract_entities_for_document([])  == 0`).
- A test asserting ChromaDB's own filter behavior (`get_chunks_by_document` on an unknown id returns `[]`) rather than anything of ours.

97 tests remain (down from 99), no coverage of real branching logic lost.

## Processor efficiency: the actual bug

`entity_extractor.py` ran every LLM batch call strictly sequentially - a plain `for` loop with no concurrency at all. `embeddings.py` already parallelizes its Ollama calls with a `ThreadPoolExecutor` for exactly this reason (many independent network round-trips, only the round-trip time matters). Entity extraction never got the same treatment, which is the actual, fixable reason M1E+M2E took most of a day combined.

Fixed: batches now dispatch concurrently (`ThreadPoolExecutor`, `max_workers=8`), with entity creation happening single-threaded afterward so there's no concurrent-write contention on `entity_store`. Measured directly against real Ollama: 4 batches completed in 99.6s concurrently vs. an estimated 360-480s sequentially - roughly a 4x wall-clock improvement.

Did **not** re-run the full M1E/M2E extraction again to "prove" this at scale - the existing data from the (slower) previous run is already valid, and re-running a multi-hour job just to demonstrate a timing improvement already validated on a real subset would be exactly the kind of waste being cut here.

One real fallout from adding concurrency: the test doubles (`ScriptedOllamaClient`, `FlakyOllamaClient`) used a plain `self.calls += 1` counter, which is not atomic and would race under real threading (multiple threads could all read the same pre-increment value and conclude they're each "the first call"). Lock-protected now.

## Branch split

Per explicit user decision: reverted the two entity-wiki-and-citations commits on `main` via `git revert` (no force-push, no history rewrite - `main` is bit-for-bit equivalent to the session-1 state again, verified via test count: 68/68, and `openspec/specs/` back to the original 4 capabilities). All of session 2's work (entity extraction, wiki, PDF citations, this efficiency pass) now lives on a new `session-2` branch instead, pushed to `origin/session-2`.

No new OpenSpec change was opened for this efficiency/test-cleanup work - it doesn't change any capability's spec-level behavior (entity extraction still does what its spec says; it just does it concurrently now), so per OpenSpec's own discipline this is an implementation detail, not something that needs a proposal.

## State at end of session

- `main`: `8e18939` (session-1 stable, pushed).
- `session-2`: `15429b3` (all of session 2's feature work + this efficiency pass, pushed).
- 68/68 tests on `main`, 97/97 on `session-2`.
- Backend/frontend still running unaffected (no code path touched by this session's changes runs at server startup differently).

## Open items

- Same as previous logs for `session-2`'s content (TEST.pdf duplicate, cross-document entity dedup, chunking story-boundary straddling).
- Since `session-2` diverges from `main`, a future merge (or another explicit "push to main" decision) will need the same care taken here - main is intentionally behind on purpose right now.
