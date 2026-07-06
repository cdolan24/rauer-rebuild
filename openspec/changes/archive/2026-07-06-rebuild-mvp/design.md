## Context

The prior build (V1) used FastAgent as a CLI-based multi-agent framework (orchestrator, analyst, web-search, retrieval agents) against cloud models. A later, unimplemented plan (V2, `base/rebuild_reference_2026-07-05/`) proposed keeping the same 4-agent FastAgent structure but swapping in Ollama-served local models, plus FastAPI and Gradio. That plan reached ~82% of a 6-week schedule before the project went stale, without ever producing a working end-to-end chat experience.

This rebuild treats V2 as reference material, not a blueprint to re-implement verbatim. The goal for this change is the smallest architecture that gets PDFs into a queryable, cited, local-LLM chatbot — deferring multi-agent orchestration until there's a concrete second agent to justify it.

## Goals / Non-Goals

**Goals:**
- Ingest the Malifaux story PDFs in `data/` into chunked, embedded, searchable form.
- Answer natural-language questions with explanatory, cited responses, using only local models (Ollama).
- Expose this through a REST API and a minimal web chat UI with a document/citation viewer.
- Keep the system runnable entirely on a single local machine with no cloud API keys.

**Non-Goals:**
- Multi-agent orchestration (separate analyst / web-search / orchestrator agents) — not needed until a capability requires more than retrieve-then-generate.
- Automated wiki generation from tagged entities — future change, once RAG is working end-to-end.
- Multi-user auth, cloud deployment, Docker packaging.
- Production-grade vector DB (Qdrant) — ChromaDB is sufficient at this document scale.

## Decisions

**1. Skip the FastAgent framework; use a plain Python retrieve-then-generate pipeline.**
V1/V2 adopted FastAgent for MCP-native multi-agent tool calling across 4 agents. This MVP only needs one flow: embed query → search vector DB → build prompt with retrieved chunks → call local LLM → return answer + citations. A framework built for multi-agent MCP orchestration adds a dependency and conceptual overhead (agent definitions, MCP tool schemas, generic-provider config) with no payoff at this scope. Citations are attached programmatically from chunk metadata rather than trusted to the LLM, which also removes the need for tool-calling reliability from the model. Revisit if/when a second distinct agent (e.g. web search) is actually needed.

**2. Vector database: ChromaDB (embedded/local), not Qdrant.**
ChromaDB needs no separate server process and persists to disk, matching a single-user local MVP. Qdrant's operational benefits (scale, Docker deployment) aren't relevant yet; keep the vector-store access behind a small interface so swapping later is a contained change.

**2a. (Amendment, found during manual verification) Use cosine similarity, not raw L2 distance, for chunk scores.** ChromaDB's default HNSW space is squared L2 distance; converting it to a "higher is better" score via `1/(1+distance)` produced values around 0.003-0.005 even for genuinely relevant `nomic-embed-text` matches, because the raw distance scale depends on embedding magnitude, not just direction. That made any fixed `min_score` threshold either always-fail (too high) or always-pass (too low) - which is exactly what happened: the chat silently gave the "no information" fallback for real, relevant questions against real ingested content. Collections are now created with `hnsw:space: cosine`, and score = `1 - distance` recovers cosine similarity directly (bounded, ~0.6-0.7 for relevant matches vs ~0.45-0.5 for irrelevant ones in practice). `min_score` is now a configurable value (`rag.min_score` in `config.yaml`, default `0.55`) rather than hardcoded, so it can be retuned if the embedding model changes.

**3. PDF extraction: PyMuPDF (`fitz`).**
Fast, handles the multi-hundred-page story PDFs well, and gives per-page text needed for citations. Alternatives (pdfplumber, pypdf) were considered but offer no advantage for this text-only use case (no OCR requirement identified).

**4. Chunking: recursive/semantic text splitting with page + document metadata per chunk.**
Chunk size ~800 chars with ~150 overlap (tunable via config), splitting on paragraph/sentence boundaries first. Every chunk stores `document_id`, `page_start`/`page_end`, and `chunk_id` so the RAG layer can cite sources without re-deriving them from the LLM.

**5. Embeddings + generation: served by Ollama, called directly over its OpenAI-compatible HTTP API.**
- Embedding model: `nomic-embed-text`.
- Generation model: a single configurable chat model (e.g. `llama3.2` or `qwen2.5`), selected in `config.yaml` — no per-agent model matrix needed since there's one agent.
No FastAgent "generic provider" indirection — a thin `OllamaClient` wrapper is enough and is easier to test/mock.

**6. API: FastAPI + Pydantic + uvicorn.**
Endpoints: `POST /api/chat`, `GET /api/documents`, `GET /api/documents/{id}`, `POST /api/documents/upload`, `POST /api/search`, `GET /api/health`. Kept from the V2 reference design since it's a reasonable, uncontroversial REST shape — this is implementation detail, not a rethink target.

**7. Frontend: Gradio.**
Fastest path to a split chat + document-viewer UI with built-in chat components; avoids hand-rolling a SPA for an MVP. Streamlit was considered as an alternative (more layout control) but Gradio's chat primitives are a better fit here.

**8. Metadata & logging: SQLite.**
A `document_registry` table tracks ingestion status per PDF; a `query_log` table records queries/response times for later analysis. Both are implementation detail, not separate specs.

**9. Configuration: single `config.yaml` (+ `.env` for anything secret/path-specific).**
No separate `fastagent.config.yaml`, since there's no FastAgent dependency (see Decision 1).

## Risks / Trade-offs

- **[Risk]** Local models (llama3.2/qwen2.5 class) may produce lower-quality explanatory answers than the cloud models V1 used → **Mitigation**: citations are attached deterministically from retrieval metadata, not generated by the model, and the generation model is swappable via config so quality can be tuned per available hardware.
- **[Risk]** Large PDF ingestion (very long documents) could be slow or memory-heavy → **Mitigation**: batch/paginated processing with progress reporting, chunk-size ceiling for large documents (per V2 reference's approach).
- **[Risk]** ChromaDB may not scale if the document set grows far beyond the current 2-3 PDFs → **Mitigation**: isolate vector-store access behind an interface so migrating to Qdrant later doesn't touch ingestion/RAG logic.
- **[Risk]** Dropping multi-agent orchestration now could mean rework if web-search or analyst-style capabilities are added later → **Mitigation**: retrieval logic is isolated in its own module so a future orchestrator can call it as one tool among several, without restructuring the RAG core.
- **[Risk]** Ollama must be running locally with the right models pulled, or nothing works → **Mitigation**: `GET /api/health` checks Ollama connectivity and reports which models are loaded; setup steps documented in tasks.md.

## Migration Plan

Greenfield build — no existing running system to migrate from or roll back to. Bring-up order:
1. Install Ollama, pull `nomic-embed-text` and the chosen chat model.
2. Run the ingestion script against `data/` to populate the vector DB and document registry.
3. Start the FastAPI backend.
4. Start the Gradio frontend and verify end-to-end chat with citations against the ingested PDFs.

## Open Questions

- Does `nomic-embed-text` retrieve well against Malifaux-specific terminology, or does it need a domain-tuned/alternative embedding model? To be evaluated once ingestion is running.
- What hardware (RAM/GPU) is actually available for running Ollama models, which constrains which chat model is practical?
- Should entity extraction (for the future wiki-generation capability) be designed for now even though it's out of scope, to avoid reprocessing PDFs twice? Leaning no — treat as a fully separate future change once RAG is proven out.
