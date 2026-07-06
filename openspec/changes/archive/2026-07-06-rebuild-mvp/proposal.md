## Why

The previous Buddharauer build (V1) is roughly 8 months stale and was never brought to a usable state. Rather than patch forward, the project is being rebuilt from first principles, driven by OpenSpec, with Claude Code doing the majority of implementation. The goal is a working local-first pipeline that turns Malifaux story PDFs into a citation-backed RAG chatbot, laying the foundation for a later auto-generated wiki.

## What Changes

- Add a document ingestion pipeline: PDF text extraction, semantic chunking, embedding generation, and storage in a local vector database.
- Add a local-LLM RAG chat capability: retrieval of relevant chunks and generation of explanatory, cited answers using models served by Ollama (no cloud LLM calls at runtime).
- Add a REST API exposing chat, document, and search operations to a frontend.
- Add a chat frontend (chat window + source document viewer with citations) for interactive Q&A.
- Establish project scaffolding (config system, dependency management, test suite structure) needed to support the above.

## Capabilities

### New Capabilities
- `document-ingestion`: Extracting text from Malifaux story PDFs, chunking it semantically, generating embeddings, and persisting chunks + metadata in a vector database.
- `rag-chat`: Answering natural-language questions about ingested documents using retrieval-augmented generation over local Ollama models, with source citations (document + page).
- `chat-api`: REST API (chat, documents, search, health) that wraps the ingestion and RAG-chat capabilities for use by a frontend.
- `chat-frontend`: Web-based chat interface with a document viewer, showing responses and their source citations side-by-side.

### Modified Capabilities
(none — this is a ground-up rebuild with no pre-existing specs)

## Impact

- **New code**: ingestion pipeline, vector store integration, RAG agent(s), REST API, web frontend, project config/scaffolding.
- **Dependencies**: Python 3.x, a PDF text extraction library, a vector database (e.g. ChromaDB), Ollama for local model serving, a web API framework, a frontend framework, pytest for testing.
- **Data**: consumes existing PDFs in `data/` (`MalifauxStories_M1E_DRAFT_5.17.2023.pdf`, `MalifauxStories_M2E_DRAFT_5.17.2023.pdf`, plus test fixtures).
- **Reference material**: `base/rebuild_reference_2026-07-05/` (old V2 architecture, implementation plan, scripts) is used as historical input to the design, not copied as-is.
- **Out of scope for this change**: automated wiki generation from tagged entities, multi-user auth, cloud deployment — these remain future work.
