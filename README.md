# Buddharauer

AI-powered document intelligence for Malifaux story/lore PDFs. Ingests story text into a
local vector database and answers questions about it through a citation-backed RAG chatbot,
running entirely on local models via [Ollama](https://ollama.ai/) - no cloud API calls.

See `openspec/changes/rebuild-mvp/` for the design rationale and full task breakdown behind
this build.

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed and running

Pull the models this project uses:

```bash
ollama pull llama3.2:latest
ollama pull qwen2.5:latest
ollama pull nomic-embed-text:latest
```

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # adjust paths/models if needed
```

## Ingest documents

Place PDFs in `data/` (a couple of Malifaux story drafts are already there), then run:

```bash
python scripts/process_documents.py            # ingest every PDF in data/
python scripts/process_documents.py data/foo.pdf  # or just one file
```

This extracts text, chunks it, generates embeddings via Ollama, and stores everything in
the local ChromaDB vector store (`vector_db/`) and a SQLite document registry
(`data_storage/`).

## Run the app

```bash
# Terminal 1: backend API
uvicorn src.api.main:app --reload --port 8000

# Terminal 2: frontend
python src/frontend/app.py
```

Open the frontend (default `http://localhost:7860`) to chat with the ingested documents
and browse sources. API docs are available at `http://localhost:8000/docs`.

## Tests

```bash
pytest
pytest --cov=src --cov-report=term-missing
```

Unit and integration tests use a fake Ollama client (see `tests/conftest.py`) so they run
without a live Ollama service. Manual verification against the real service is documented
in `openspec/changes/rebuild-mvp/tasks.md` (section 6).
