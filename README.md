# Malifaux Document Explorer

AI-powered document intelligence for Malifaux story/lore PDFs. Ingests story text into a
local vector database and answers questions about it through a citation-backed RAG chatbot.
Embeddings always run locally via [Ollama](https://ollama.ai/). Chat generation (RAG answers,
wiki summaries, entity extraction) runs on Ollama too by default - fully local, no cloud API
calls - or can be routed to a hosted API instead (see "Deployment" below) for deployments that
don't want to pay for a GPU instance just to run a local chat model.

See `openspec/changes/archive/2026-07-06-rebuild-mvp/` for the design rationale and full
task breakdown behind this build.

## Status

**Functionally complete.** Every planned OpenSpec change has been implemented and archived
(`openspec/changes/archive/`), with no active changes outstanding. The current capability
specs live in `openspec/specs/`. Further work would be maintenance or new features rather
than finishing the original scope.

This project supersedes the earlier `buddharauer` and `rauer-test` repositories, which were
prior iterations of the same app and are kept only for reference.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running

Pull the models this project uses:

```bash
ollama pull llama3.2:latest
ollama pull nomic-embed-text:latest
```

## Setup

```bash
pip install ".[dev]"   # omit "[dev]" if you don't need the test suite
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

## Deployment

`deploy/setup_ec2.sh` (AWS) and `deploy/setup_azure_vm.sh` (Azure) each provision a
single host (systemd + Nginx, no containers - see `openspec/specs/deployment/`) under
one of two profiles, selected via `DEPLOY_PROFILE`. See `deploy/README.md` for full
setup instructions on either cloud.

| Profile | AWS instance / Azure VM size | Chat generation | Embeddings | When to use |
|---|---|---|---|---|
| `gpu-inhouse` (default) | GPU-backed, e.g. `g4dn.xlarge` / `Standard_NC4as_T4_v3` | Local Ollama (`llama3.2`) | Local Ollama | Hardware you already own - fully local, no cloud LLM calls |
| `cpu-hosted-api` | Small CPU-only, e.g. `t3.small` / `Standard_B2s` | Hosted API (`hosted_llm` in `config.yaml`, default Anthropic's `claude-haiku-4-5`) | Local Ollama | Cost-optimized - a GPU instance running 24/7 just to serve chat generation costs far more than a hosted API does for typical usage of this app |

```bash
# In-house / GPU (default) - AWS
sudo UDC_REPO_URL=https://github.com/you/rauer-rebuild.git ./deploy/setup_ec2.sh

# Cost-optimized, no GPU - AWS
sudo UDC_REPO_URL=https://github.com/you/rauer-rebuild.git DEPLOY_PROFILE=cpu-hosted-api ./deploy/setup_ec2.sh

# In-house / GPU (default) - Azure
sudo UDC_REPO_URL=https://github.com/you/rauer-rebuild.git ./deploy/setup_azure_vm.sh

# Cost-optimized, no GPU - Azure
sudo UDC_REPO_URL=https://github.com/you/rauer-rebuild.git DEPLOY_PROFILE=cpu-hosted-api ./deploy/setup_azure_vm.sh
```

Under `cpu-hosted-api`, set a real `hosted_llm.api_key` in `config.yaml` before starting
services - the app fails fast at startup rather than on the first chat request if it's left
as the placeholder. Embeddings and the optional vision model always run on local Ollama in
both profiles; only chat generation moves to the hosted API.

## Tests

```bash
pytest
pytest --cov=src --cov-report=term-missing
```

Unit and integration tests use a fake Ollama client (see `tests/conftest.py`) so they run
without a live Ollama service. Manual verification against the real service is documented
in `openspec/changes/archive/2026-07-06-rebuild-mvp/tasks.md` (section 6).
