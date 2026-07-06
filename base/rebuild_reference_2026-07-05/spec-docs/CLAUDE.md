# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview - ARCHITECTURE V2 (HYBRID APPROACH!)

**Buddharauer** is a local-first AI-powered PDF analysis system with a **chat-based web interface**. Built with **FastAgent + FastAPI + Ollama**, it combines the power of FastAgent's MCP-native agent framework with local LLMs, exposing agents via REST API for web frontend access.

**⚠️ IMPORTANT**: The architecture uses a **hybrid approach**: FastAgent agents (orchestration) + FastAPI (REST layer) + Ollama (local models) + Gradio (web UI). See `specs/ARCHITECTURE_V2.md` for complete details.

## Technology Stack V2

- **Agent Framework**: FastAgent (fast-agent-mcp v0.3.17+)
- **Backend**: FastAPI (REST API wrapping FastAgent agents)
- **Frontend**: Gradio (web chat interface with document viewer)
- **LLM Server**: Ollama (local models: llama3.2, qwen2.5, mistral, phi)
- **Agent Integration**: FastAgent generic provider → Ollama OpenAI-compatible API
- **Vector Database**: ChromaDB (MVP) or Qdrant (production)
- **PDF Processing**: PyMuPDF (fitz), Pillow
- **Python**: 3.13.5+ (required for FastAgent)
- **Package Manager**: uv (preferred) or pip
- **Testing**: pytest, pytest-asyncio, httpx

## Key Features

### Chat-Based Interface (NEW!)
- **Split Screen UI**: Chat window + Source document viewer side-by-side
- **Live Citations**: Highlighted passages with page references
- **Multi-Turn Conversations**: Context-aware dialogue

### Local-First Architecture (NEW!)
- **No Cloud Dependencies**: All models run via Ollama
- **Privacy**: Documents never leave your machine
- **Configurable Models**: Choose models per agent based on hardware

### Multi-Agent System (FastAgent)
- **Orchestrator Agent**: Main FastAgent agent, routes questions, manages conversation (generic.llama3.2:latest)
- **Analyst Agent**: FastAgent sub-agent, summarizes and provides insights (generic.llama3.2:latest or qwen2.5)
- **Web Search Agent**: FastAgent sub-agent, external search via MCP tools (generic.mistral:7b)
- **Retrieval Agent**: FastAgent sub-agent, RAG system for vector search (generic.qwen2.5:latest + nomic-embed-text embeddings)

## Project Structure V2

```
buddharauer/
├── config.yaml              # Main configuration (NEW!)
├── requirements.txt         # Python dependencies
├── run.py                   # Application launcher (NEW!)
│
├── data/                    # Raw PDFs
├── processed/               # Processed outputs
│   ├── text/
│   ├── markdown/
│   ├── metadata/
│   └── images/
├── vector_db/              # ChromaDB/Qdrant
├── data_storage/           # SQLite databases
│
├── src/
│   ├── api/               # FastAPI backend (NEW!)
│   │   ├── main.py       # API entry point
│   │   └── routes/       # /chat, /documents, /search, /health
│   │
│   ├── agents/           # LangChain agents (NEW!)
│   │   ├── orchestrator.py
│   │   ├── analyst.py
│   │   ├── web_search.py
│   │   └── retrieval.py
│   │
│   ├── pipeline/         # Document processing
│   │   ├── pdf_extractor.py
│   │   ├── chunker.py         # Semantic chunking (NEW!)
│   │   ├── embeddings.py
│   │   └── image_processor.py
│   │
│   ├── database/
│   │   ├── vector_store.py
│   │   ├── document_registry.py
│   │   └── query_logger.py
│   │
│   ├── frontend/         # Gradio UI (NEW!)
│   │   ├── app.py
│   │   └── components/
│   │
│   └── utils/
│       ├── config.py          # YAML config loader
│       ├── ollama_client.py   # Ollama API wrapper
│       └── chunking.py
│
├── tests/
│   ├── unit/
│   ├── integration/      # API tests, agent tests
│   └── e2e/             # Full chat flow tests
│
├── scripts/
│   ├── process_documents.py
│   └── setup_models.py
│
└── specs/               # Documentation
    ├── ARCHITECTURE_V2.md      # **READ THIS FIRST!**
    ├── IMPLEMENTATION_PLAN.md  # Development roadmap
    └── API.md                  # REST API reference
```

## Configuration Files

### fastagent.config.yaml (FastAgent LLM Provider)

```yaml
# FastAgent generic provider for Ollama
generic:
  api_key: "ollama"
  base_url: "http://localhost:11434/v1"  # Ollama OpenAI-compatible endpoint
```

### config.yaml (Application Configuration)

```yaml
# FastAgent + Ollama setup
fastagent:
  provider: "generic"
  ollama_base_url: "http://localhost:11434"
  models_path: "/custom/path"  # Optional

# Agent model selections (FastAgent model specs)
agents:
  orchestrator:
    model: "generic.llama3.2:latest"
    temperature: 0.7
  analyst:
    model: "generic.llama3.2:latest"
    temperature: 0.5
  web_search:
    model: "generic.mistral:7b"
    temperature: 0.3
  retrieval:
    llm_model: "generic.qwen2.5:latest"
    embedding_model: "nomic-embed-text"

vector_db:
  type: "chromadb"
  path: "./vector_db"

chunking:
  strategy: "semantic"
  chunk_size: 800
  chunk_overlap: 150
```

## Recommended LLM Models (FastAgent + Ollama)

| Agent | FastAgent Model Spec | Ollama Model | RAM | GPU | FastAgent Tested |
|-------|---------------------|--------------|-----|-----|------------------|
| Orchestrator | `generic.llama3.2:latest` | llama3.2 | 8GB | Optional | ✅ Yes |
| Orchestrator (alt) | `generic.qwen2.5:latest` | qwen2.5 | 7GB | Optional | ✅ Yes |
| Analyst | `generic.llama3.2:latest` | llama3.2 | 8GB | Optional | ✅ Yes |
| Web Search | `generic.mistral:7b` | mistral:7b | 6GB | Optional | ⚠️ Limited |
| Retrieval (LLM) | `generic.qwen2.5:latest` | qwen2.5 | 7GB | Optional | ✅ Yes |
| Embeddings | N/A (Ollama API) | nomic-embed-text | 2GB | - | N/A |

**Note**: FastAgent has officially tested tool calling and structured generation with `llama3.2:latest` and `qwen2.5:latest`. Other models may work but are not guaranteed.

**Alternatives**:
- Low memory: `phi3:mini` (4GB), `mistral:7b` (6GB)
- High quality: `llama3:70b` (40GB), `qwen2:72b` (40GB)

## Quick Start Commands

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models for FastAgent
ollama pull llama3.2:latest
ollama pull qwen2.5:latest
ollama pull mistral:7b
ollama pull nomic-embed-text

# Install dependencies (requires Python 3.13.5+)
uv pip install -r requirements.txt
# Or: pip install -r requirements.txt

# Setup FastAgent
fast-agent setup  # Creates fastagent.config.yaml

# Configure Ollama in fastagent.config.yaml:
# generic:
#   api_key: "ollama"
#   base_url: "http://localhost:11434/v1"

# Test FastAgent + Ollama
fast-agent --model generic.llama3.2:latest

# Process documents
python scripts/process_documents.py

# Start backend (FastAPI + FastAgent)
uvicorn src.api.main:app --reload --port 8000

# Start frontend (Gradio)
python src/frontend/app.py

# Or use launcher
python run.py
```

## REST API Endpoints

### Chat
- `POST /api/chat` - Send message, get response with sources
- `GET /api/conversations/{id}` - Get chat history
- `DELETE /api/conversations/{id}` - Clear conversation

### Documents
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}` - Get document details
- `GET /api/documents/{id}/content` - Get markdown/text
- `POST /api/documents/upload` - Upload new PDF

### Search
- `POST /api/search` - Vector search across documents

### Health
- `GET /api/health` - System status, Ollama connectivity

## Development Workflow

### 1. Setup Environment
```bash
# Install Ollama and pull models
# Create venv and install dependencies
# Copy config.example.yaml to config.yaml
```

### 2. Process Documents
```bash
# Add PDFs to data/
python scripts/process_documents.py
```

### 3. Start Development
```bash
# Terminal 1: Backend
uvicorn src.api.main:app --reload

# Terminal 2: Frontend
python src/frontend/app.py

# Access: http://localhost:7860
```

### 4. Testing
```bash
# Run all tests
pytest

# Run specific category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# With coverage
pytest --cov=src --cov-report=html
```

## Large PDF Handling

### Chunking Strategy
```python
# Semantic chunking with LangChain
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,          # Configurable in config.yaml
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
)
```

### Chunk Metadata
```python
{
    "chunk_id": "doc_001_chunk_042",
    "document_id": "doc_001",
    "page_start": 42,
    "page_end": 43,
    "chapter": "Book 1, Chapter 3",
    "text": "...",
    "embedding": [0.1, 0.2, ...]
}
```

## Important Implementation Notes

### FastAgent + Ollama Integration
- **FastAgent Layer**: All agents defined using FastAgent framework (fast-agent-mcp)
- **Ollama Connection**: FastAgent uses generic provider pointing to Ollama's OpenAI-compatible API (localhost:11434/v1)
- **Configuration**: Set via `fastagent.config.yaml` and environment variables
- **Model Specification**: Use `generic.model_name:tag` format (e.g., `generic.llama3.2:latest`)
- **Tool Calling**: Use FastAgent's MCP tools for sub-agents and vector DB access
- **Testing**: Verify tool calling works with `llama3.2:latest` or `qwen2.5:latest` (officially tested)

### FastAPI Integration
- **Wrapper Layer**: FastAPI endpoints call FastAgent agents programmatically
- **Agent Initialization**: Initialize FastAgent orchestrator on app startup
- **Async Calls**: Use async/await for agent calls from FastAPI endpoints
- **Response Formatting**: Extract sources and metadata from agent responses
- **Error Handling**: Catch FastAgent exceptions and return appropriate HTTP errors

### Agent Design (FastAgent)
- **Orchestrator**: Main FastAgent agent with sub-agent tools
- **Sub-agents**: Defined as FastAgent tools or workflows
- **Routing**: Orchestrator uses MCP tool calling to invoke sub-agents
- **Memory**: Conversation context managed by FastAgent
- **RAG**: Custom MCP tool for ChromaDB vector search

### Vector Database
- Use ChromaDB for MVP (easy setup)
- Qdrant for production (better performance)
- Batch upsert for large documents
- Include rich metadata in chunks

### Frontend (Gradio)
- Split screen: chat on left, document viewer on right
- Citations clickable → scroll document viewer
- Chat history maintained per conversation
- Document selector dropdown

### Testing Critical Services
- **Chunking**: Test with various PDF sizes
- **Embeddings**: Verify Ollama connectivity
- **Agents**: Mock Ollama responses
- **API**: Test all endpoints with httpx
- **E2E**: Full chat flow with test documents

## Common Gotchas

1. **Ollama must be running**: Check with `ollama list`
2. **Model not pulled**: Run `ollama pull <model>`
3. **Large PDFs**: May need >16GB RAM for processing
4. **Gradio CORS**: Configure in FastAPI for localhost:7860
5. **Chunking large docs**: Use progress bars, handle timeouts

## Current Status

**Architecture**: V2 (Ollama + FastAPI + Gradio)
**Phase**: 0 (Planning Complete, Ready for Implementation)
**Next**: Environment setup → Document processing pipeline → Backend API → Agents → Frontend

## Key Documentation

**MUST READ**:
- `specs/ARCHITECTURE_V2.md` - Complete V2 architecture details
- `specs/IMPLEMENTATION_PLAN.md` - 6-week development plan with GitHub issues
- `README.md` - User-facing documentation

**Reference**:
- `specs/user-stories-detailed.md` - User requirements (Faraday & Albert)
- `specs/API.md` - REST API specification (to be created)

## Architecture Changes from V1

| Aspect | V1 | V2 |
|--------|----|----|
| **Framework** | FastAgent (CLI) | FastAgent + FastAPI (Hybrid) |
| **Models** | Cloud (Claude/GPT) | Local (Ollama) |
| **Interface** | CLI | Web (Gradio) |
| **UX** | Terminal Q&A | Chat + Document Viewer |
| **Agents** | 5 FastAgent agents (CLI) | 4 FastAgent agents (via FastAPI) |
| **Model Access** | Cloud APIs | Ollama via FastAgent generic provider |
| **Config** | .env | fastagent.config.yaml + config.yaml + .env |

## Session Handoff Checklist

At end of each session:
- [ ] Update GitHub issues with progress
- [ ] Update IMPLEMENTATION_PLAN.md
- [ ] Run tests and note any failures
- [ ] Update this CLAUDE.md if architecture changes
- [ ] Document blockers or decisions needed
- [ ] List next session priorities

## Resources

- **Ollama Docs**: https://github.com/ollama/ollama
- **LangChain Docs**: https://python.langchain.com/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Gradio Docs**: https://gradio.app/
- **ChromaDB Docs**: https://docs.trychroma.com/

---

**Note**: This project uses **local models only** via Ollama. No cloud API keys required (except optional web search).

*Last updated: 2025-11-09*
*Architecture: V2 (FastAgent + FastAPI + Ollama Hybrid)*
*Status: Planning Complete, Ready for Phase 0 Implementation*
*Key Change: FastAgent framework retained, integrated with FastAPI and Ollama local models*
