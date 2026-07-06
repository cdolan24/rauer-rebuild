## 1. Project Setup

- [x] 1.1 Create project structure (`src/{pipeline,database,rag,api,frontend,utils}`, `tests/{unit,integration,e2e}`, `processed/`, `vector_db/`, `data_storage/`, `scripts/`)
- [x] 1.2 Create `pyproject.toml`/`requirements.txt` with core dependencies (pymupdf, chromadb, fastapi, uvicorn, pydantic, gradio, httpx, pytest, pytest-asyncio, pytest-cov)
- [x] 1.3 Create `config.yaml` (chunking, vector DB path, Ollama base URL, model names) and `config.example.yaml`
- [x] 1.4 Implement `src/utils/config.py` YAML config loader with validation
- [x] 1.5 Set up logging (`src/utils/logging.py`)
- [x] 1.6 Install Ollama locally and pull required models (embedding model + chosen chat model); verify with `ollama list`
- [x] 1.7 Verify Ollama HTTP API responds (`curl http://localhost:11434/api/tags`)

## 2. Document Ingestion Pipeline

- [x] 2.1 Implement `src/pipeline/pdf_extractor.py`: extract text + page boundaries via PyMuPDF; handle corrupted/unreadable files without crashing the run
- [x] 2.2 Implement `src/pipeline/chunker.py`: recursive/semantic chunking with configurable size/overlap, attaching `chunk_id`, `document_id`, `page_start`/`page_end` metadata
- [x] 2.3 Implement `src/utils/ollama_client.py`: thin HTTP client wrapper for Ollama's embeddings and chat completion endpoints
- [x] 2.4 Implement `src/pipeline/embeddings.py`: batch-generate embeddings for chunks via `OllamaClient`, surfacing a clear error if the embedding service is unreachable
- [x] 2.5 Implement `src/database/vector_store.py`: ChromaDB-backed store with insert/search operations, isolated behind a small interface
- [x] 2.6 Implement `src/database/document_registry.py`: SQLite table tracking per-document ingestion status (`pending`/`processed`/`failed`)
- [x] 2.7 Implement `scripts/process_documents.py`: CLI to ingest all PDFs in `data/` (or a single file), reporting a success/failure summary
- [x] 2.8 Write unit tests: `tests/unit/test_pdf_extractor.py`, `test_chunker.py`, `test_embeddings.py`
- [x] 2.9 Write integration test: `tests/integration/test_ingestion_pipeline.py` running the full pipeline against a small test PDF
- [x] 2.10 Run ingestion against the real `data/` PDFs and confirm chunks are retrievable from the vector store (M1E: 629 pages, 2396 chunks; verified retrieval + full chat answer with citations against real Ollama)

## 3. RAG Chat Core

- [x] 3.1 Implement `src/rag/retriever.py`: embed a query, search the vector store, return ranked chunks with metadata
- [x] 3.2 Implement `src/rag/prompt_builder.py`: build an explanatory-style generation prompt from retrieved chunks + conversation history
- [x] 3.3 Implement `src/rag/chat_engine.py`: orchestrate retrieve → prompt → generate → attach citations (from chunk metadata, not the LLM) → "no information" fallback when nothing relevant is found
- [x] 3.4 Implement `src/rag/conversation_store.py`: in-memory or SQLite-backed multi-turn conversation history keyed by conversation id
- [x] 3.5 Write unit tests: `tests/unit/test_retriever.py`, `test_prompt_builder.py`
- [x] 3.6 Write integration test: `tests/integration/test_chat_engine.py` covering grounded answer, no-relevant-content fallback, and multi-turn follow-up

## 4. FastAPI Backend

- [x] 4.1 Implement `src/api/main.py`: app setup, CORS for the frontend, error-handling middleware
- [x] 4.2 Implement Pydantic request/response models for chat, documents, search
- [x] 4.3 Implement `src/api/routes/chat.py`: `POST /api/chat`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`
- [x] 4.4 Implement `src/api/routes/documents.py`: `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/content`, `POST /api/documents/upload`
- [x] 4.5 Implement `src/api/routes/search.py`: `POST /api/search`
- [x] 4.6 Implement `src/api/routes/health.py`: `GET /api/health` checking Ollama connectivity + vector DB status + indexed document count
- [x] 4.7 Implement `src/database/query_logger.py`: log queries and response times to SQLite
- [x] 4.8 Write integration tests: `tests/integration/test_api.py` covering all endpoints (happy path + Ollama-unreachable health case)

## 5. Gradio Frontend

- [x] 5.1 Implement `src/frontend/app.py`: split-screen layout (chat panel + document viewer panel)
- [x] 5.2 Implement chat component: send message, display chat history, show citations per response
- [x] 5.3 Implement document viewer component: render selected document content, jump to a cited page
- [x] 5.4 Implement document selector + upload UI, showing ingestion status until a document becomes available
- [x] 5.5 Implement `src/frontend/api_client.py`: HTTP client calling the FastAPI backend
- [x] 5.6 Wire error/loading states (backend unreachable, empty document list, etc.)

## 6. Testing, Verification & Polish

- [x] 6.1 Write end-to-end test: `tests/e2e/test_chat_flow.py` covering ingest → ask question → receive cited answer
- [x] 6.2 Manually verify the full flow in a browser: start backend, start frontend, ask questions about the ingested Malifaux PDFs, confirm citations link to the correct document/page (verified via Playwright; caught and fixed a real min_score/scoring-scale bug in the process - see design note below)
- [x] 6.3 Confirm `GET /api/health` correctly reflects both a healthy state and an Ollama-down state (covered by tests/integration/test_api.py)
- [x] 6.4 Review test coverage; backfill gaps in ingestion, RAG core, and API layers (44 tests, ~97-100% on all backend/pipeline modules; frontend Gradio UI untested by design - no automated harness for it in this MVP)
- [x] 6.5 Write a short README/quickstart: install Ollama + models, install deps, run ingestion, start backend, start frontend
