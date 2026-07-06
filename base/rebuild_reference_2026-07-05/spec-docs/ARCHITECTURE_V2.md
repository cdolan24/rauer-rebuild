# Architecture V2 - FastAgent + FastAPI + Local Ollama Models

## Major Architecture Changes

### Previous Architecture (V1)
- **Framework**: FastAgent (fast-agent-mcp)
- **Models**: Cloud-based (Anthropic Claude, OpenAI GPT)
- **Interface**: CLI-based
- **Package Manager**: uv
- **User Experience**: Terminal-based Q&A

### New Architecture (V2) - **HYBRID APPROACH**
- **Agent Framework**: FastAgent (fast-agent-mcp) for agent orchestration
- **Backend Framework**: FastAPI REST API (exposing FastAgent agents via HTTP)
- **Models**: Local models via Ollama (configurable locations)
- **Interface**: Web-based chat with split-screen (chat + source documents)
- **Frontend**: Gradio (web UI)
- **User Experience**: Chat-like conversation with document viewer
- **Key Innovation**: FastAgent agents powered by local Ollama models, exposed via FastAPI endpoints

---

## Technology Stack V2

### Core Framework
- **Agent Framework**: FastAgent (fast-agent-mcp v0.3.17+)
  - MCP-native agent framework
  - Tool calling and structured generation
  - Multi-agent orchestration
  - Built-in prompt templates
- **Backend Framework**: FastAPI (REST API)
  - Exposes FastAgent agents via HTTP endpoints
  - Handles web frontend communication
  - Manages authentication and sessions
- **Frontend**: Gradio (web chat UI)
- **Package Manager**: uv (preferred) or pip + venv
- **Python**: 3.13.5+ (required for FastAgent)

### Local LLM Infrastructure
- **Ollama**: Primary model server for local LLMs
  - Installation: https://ollama.ai/
  - Models: llama3, mistral, phi, qwen, etc.
  - API: OpenAI-compatible REST API on localhost:11434
  - FastAgent integration: Uses generic OpenAI provider with Ollama base_url

- **FastAgent + Ollama Configuration**:
  - FastAgent's generic provider supports Ollama out-of-the-box
  - Configuration via `fastagent.config.yaml`
  - Environment variables: `GENERIC_API_KEY`, `GENERIC_BASE_URL`
  - Model specification: `generic.llama3.2:latest`, `generic.qwen2.5:latest`

- **Note**: LangChain removed in favor of FastAgent's native agent framework

### Vector Database
- **ChromaDB** (MVP): Local, easy setup
- **Qdrant** (Production): Better performance, Docker deployment
- Both support local deployment

### PDF Processing
- **PyMuPDF (fitz)**: Text + image extraction
- **Pillow**: Image processing
- **pytesseract** (optional): OCR

### Backend API
- **FastAPI**: Modern Python REST API framework
- **Pydantic**: Data validation
- **uvicorn**: ASGI server

### Frontend
- **Gradio** (Recommended):
  - Quick chat interface
  - Built-in chat components
  - Document viewer support
  - Easy deployment

- **Streamlit** (Alternative):
  - More customization
  - Better for complex layouts
  - Larger community

### Testing
- **pytest**: Unit and integration tests
- **pytest-asyncio**: Async testing
- **httpx**: API testing

### Authentication (Optional MVP)
- **JWT**: Token-based auth
- **bcrypt**: Password hashing
- **SQLite**: User database

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Gradio/Streamlit)                │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │   Chat Interface     │    │   Document Viewer            │  │
│  │   (User Messages)    │    │   (Source PDFs/Markdown)     │  │
│  │   (Agent Responses)  │    │   (Highlighted Citations)    │  │
│  └──────────────────────┘    └──────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │ HTTP/WebSocket
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (REST API)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  API Endpoints:                                           │  │
│  │  - /chat (POST) - Send message to FastAgent orchestrator │  │
│  │  - /documents (GET) - List documents                     │  │
│  │  - /documents/{id} (GET) - Get document content          │  │
│  │  - /upload (POST) - Upload PDF                           │  │
│  │  - /health (GET) - System health                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│             FastAgent Agent Orchestration Layer                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAgent Orchestrator (Main Agent)                     │   │
│  │  - Model: generic.llama3.2:latest via Ollama            │   │
│  │  - Understands user intent                               │   │
│  │  - Routes to sub-agents using MCP tools                  │   │
│  │  - Manages conversation context                          │   │
│  │  - Formats responses for UI                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Analyst     │  │  Web Search  │  │  Document Retrieval  │  │
│  │  Agent       │  │  Agent       │  │  Agent (RAG)         │  │
│  │  (FastAgent) │  │  (FastAgent) │  │  (FastAgent)         │  │
│  │              │  │              │  │                      │  │
│  │  Model:      │  │  Model:      │  │  Model:              │  │
│  │  generic.    │  │  generic.    │  │  generic.qwen2.5     │  │
│  │  llama3.2    │  │  mistral:7b  │  │  + nomic-embed-text  │  │
│  │              │  │              │  │                      │  │
│  │  Summarizes  │  │  Searches    │  │  Finds relevant      │  │
│  │  data and    │  │  web for     │  │  chunks from         │  │
│  │  provides    │  │  external    │  │  vector DB           │  │
│  │  insights    │  │  info        │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │ (All agents use FastAgent framework)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Local LLM Layer (Ollama)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Ollama Server (localhost:11434)                         │   │
│  │  - OpenAI-compatible API endpoint: /v1/chat/completions │   │
│  │  - Models: llama3.2, mistral:7b, qwen2.5, phi3         │   │
│  │  - Embeddings: nomic-embed-text                         │   │
│  │  - Model path: /models/ or custom location              │   │
│  │  - FastAgent connects via generic provider config       │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Storage Layer                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │  Vector DB │  │  Document  │  │   Images   │  │  SQLite  │  │
│  │ (ChromaDB/ │  │   Store    │  │   Store    │  │ (Metadata│  │
│  │  Qdrant)   │  │ (Markdown) │  │ (PNG/JPEG) │  │  & Logs) │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Design

### 1. Orchestrator Agent (FastAgent)

**Purpose**: Main user-facing agent that coordinates all interactions

**Implementation**: FastAgent main agent with tool calling to sub-agents

**Responsibilities**:
- Parse user messages and understand intent
- Maintain conversation context and history
- Route requests to appropriate sub-agents via MCP tools
- Combine responses from multiple agents
- Format responses for chat UI
- Generate citations and source references

**Model Configuration** (via FastAgent):
- **Primary**: `generic.llama3.2:latest` (tested with FastAgent tool calling)
- **Alternative**: `generic.qwen2.5:latest` (better structured generation)
- **High-quality**: `generic.llama3:70b` (if hardware allows)

**FastAgent Configuration**:
```yaml
# In fastagent.config.yaml
generic:
  api_key: "ollama"
  base_url: "http://localhost:11434/v1"

# Run with:
# fast-agent --model generic.llama3.2:latest
```

**Key Capabilities**:
- Intent classification (question, summarization, search, etc.)
- Context window management
- Multi-turn conversation
- MCP tool calling to sub-agents
- Structured output generation

---

### 2. Analyst Agent (FastAgent)

**Purpose**: Summarize and analyze document content

**Implementation**: FastAgent sub-agent called via MCP tool from orchestrator

**Responsibilities**:
- Generate entity summaries (characters, locations, items)
- Create thematic analyses
- Identify patterns and connections
- Provide creative insights and context (for Faraday user profile)
- Aggregate information across documents

**Model Configuration** (via FastAgent):
- **Primary**: `generic.llama3.2:latest` or `generic.qwen2.5:latest` (structured output)
- **Alternative**: `generic.phi3:medium` (efficient, good reasoning)

**Configuration**:
```yaml
# Can be defined as separate agent or workflow in FastAgent
agent_name: "analyst"
model: "generic.llama3.2:latest"
temperature: 0.5  # Lower for more focused analysis
```

**Key Capabilities**:
- Structured output generation
- Multi-document synthesis
- Creative/thematic analysis
- Entity relationship mapping

---

### 3. Web Search Agent (FastAgent)

**Purpose**: Search external web sources when needed

**Implementation**: FastAgent sub-agent with MCP web search tools

**Responsibilities**:
- Determine when external search is needed
- Formulate search queries
- Fetch and parse web results (via MCP tools)
- Summarize findings
- Cite sources

**Model Configuration** (via FastAgent):
- **Primary**: `generic.mistral:7b` (fast, good at summarization)
- **Alternative**: `generic.phi3:mini` (very fast for query generation)

**MCP Tools Integration**:
- FastAgent can use MCP web search servers
- DuckDuckGo MCP server (no API key needed)
- Brave Search MCP server
- Custom search tools via MCP protocol

**Configuration**:
```yaml
agent_name: "web_search"
model: "generic.mistral:7b"
temperature: 0.3  # Low for factual search
mcp_servers:
  - duckduckgo-search
```

**Key Capabilities**:
- Query formulation
- Result filtering and ranking
- Web content summarization via MCP tools
- Source validation

---

### 4. Document Retrieval Agent (RAG) - FastAgent

**Purpose**: Retrieve relevant chunks from vector database

**Implementation**: FastAgent sub-agent with custom MCP tool for vector DB access

**Responsibilities**:
- Convert user query to embedding
- Search vector database for relevant chunks via MCP tool
- Rank and filter results
- Provide context to orchestrator
- Track citations (document, page, chunk)

**Model Configuration**:
- **LLM**: `generic.qwen2.5:latest` (for query reformulation and ranking)
- **Embedding Model**: `nomic-embed-text` (via Ollama embeddings endpoint)
- **Alternative Embeddings**: `all-MiniLM-L6-v2` (HuggingFace)
- **High-quality**: `bge-large-en-v1.5` (better but slower)

**MCP Tool Integration**:
```yaml
agent_name: "retrieval"
model: "generic.qwen2.5:latest"
mcp_tools:
  - name: "vector_search"
    description: "Search ChromaDB for relevant document chunks"
  - name: "get_chunk_context"
    description: "Get surrounding chunks for context"
```

**Key Capabilities**:
- Semantic search via embeddings
- Hybrid search (dense + sparse)
- Re-ranking with LLM
- Citation generation with page numbers
- Context expansion

---

## Recommended LLM Matrix (FastAgent + Ollama)

| Agent | FastAgent Model Spec | Ollama Model | Speed | Quality | Memory | FastAgent Tested |
|-------|---------------------|--------------|-------|---------|--------|------------------|
| **Orchestrator** | `generic.llama3.2:latest` | llama3.2 | Medium | High | 8GB | ✅ Yes |
| **Orchestrator** (alt) | `generic.qwen2.5:latest` | qwen2.5 | Medium | High | 7GB | ✅ Yes |
| **Analyst** | `generic.llama3.2:latest` | llama3.2 | Medium | High | 8GB | ✅ Yes |
| **Analyst** (alt) | `generic.qwen2.5:latest` | qwen2.5 | Medium | High | 7GB | ✅ Yes |
| **Web Search** | `generic.mistral:7b` | mistral:7b | Fast | Medium | 6GB | ⚠️ Limited |
| **Web Search** (alt) | `generic.phi3:mini` | phi3:mini | Very Fast | Medium | 4GB | ⚠️ Limited |
| **RAG/Retrieval** | `generic.qwen2.5:latest` | qwen2.5 | Medium | High | 7GB | ✅ Yes |
| **Embeddings** | N/A (Ollama API) | nomic-embed-text | Fast | High | 2GB | N/A |

**Note**: FastAgent has tested tool calling and structured generation primarily with `llama3.2:latest` and `qwen2.5:latest`. Other models may work but are not officially tested.

### Hardware Requirements

**Minimum (for testing)**:
- RAM: 16GB
- GPU: Optional (CPU mode works)
- Disk: 20GB for models

**Recommended**:
- RAM: 32GB
- GPU: NVIDIA with 8GB+ VRAM (RTX 3070 or better)
- Disk: 50GB for models + data

**Optimal**:
- RAM: 64GB
- GPU: NVIDIA with 16GB+ VRAM (RTX 4080 or better)
- Disk: 100GB+ SSD

---

## Configuration System

### FastAgent Configuration (fastagent.config.yaml)

```yaml
# FastAgent LLM provider configuration
generic:
  api_key: "ollama"  # Default for Ollama
  base_url: "http://localhost:11434/v1"  # Ollama OpenAI-compatible endpoint

# Optional: Override with environment variables
# GENERIC_API_KEY=ollama
# GENERIC_BASE_URL=http://localhost:11434/v1
```

### Application Configuration (config.yaml)

```yaml
# FastAgent + Ollama configuration
fastagent:
  provider: "generic"  # Use generic provider for Ollama
  ollama_base_url: "http://localhost:11434"
  models_path: "/path/to/ollama/models"  # Configurable model location

# Agent-specific model selections
agents:
  orchestrator:
    model: "generic.llama3.2:latest"  # FastAgent model spec
    temperature: 0.7
    max_tokens: 2048

  analyst:
    model: "generic.llama3.2:latest"
    temperature: 0.5
    max_tokens: 4096

  web_search:
    model: "generic.mistral:7b"
    temperature: 0.3
    max_tokens: 1024

  retrieval:
    llm_model: "generic.qwen2.5:latest"  # For query reformulation
    embedding_model: "nomic-embed-text"  # Via Ollama embeddings API
    dimensions: 768

# Vector database configuration
vector_db:
  type: "chromadb"  # or "qdrant"
  path: "./vector_db"
  collection_name: "buddharauer_docs"

# Chunking configuration for large PDFs
chunking:
  strategy: "semantic"  # or "fixed", "recursive"
  chunk_size: 800  # tokens
  chunk_overlap: 150
  max_chunk_size: 1500
  min_chunk_size: 100

  # For very large PDFs
  large_pdf_threshold: 10000  # pages
  large_pdf_chunk_size: 500  # smaller chunks for large docs

# API configuration
api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:7860"]  # Gradio default

# Frontend configuration
frontend:
  platform: "gradio"  # or "streamlit"
  theme: "soft"
  chat_history_length: 50
  document_viewer: true
```

---

## Large PDF Handling

### Chunking Strategy for Large PDFs

**Problem**: Large PDFs (100+ pages) need efficient chunking for vector DB storage and retrieval.

**Solution**: Multi-level chunking strategy

#### 1. **Semantic Chunking** (Recommended)
```python
# Use LangChain's semantic chunker
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)
```

#### 2. **Hierarchical Chunking**
```python
# For very large documents:
# Level 1: Chapter/section level (for summaries)
# Level 2: Paragraph level (for detailed Q&A)
# Level 3: Sentence level (for specific facts)

hierarchy = {
    "chapter": {"size": 5000, "overlap": 500},
    "section": {"size": 1500, "overlap": 200},
    "paragraph": {"size": 800, "overlap": 150},
}
```

#### 3. **Metadata Enrichment**
```python
# Each chunk includes:
{
    "chunk_id": "doc_001_chunk_042",
    "document_id": "doc_001",
    "document_title": "The Fellowship of the Ring",
    "page_start": 42,
    "page_end": 43,
    "chapter": "Book 1, Chapter 3",
    "chunk_type": "paragraph",  # chapter, section, paragraph
    "parent_chunk_id": "doc_001_chunk_040",  # for hierarchy
    "text": "...",
    "embedding": [0.1, 0.2, ...],
}
```

#### 4. **Progressive Loading**
```python
# For PDFs > 1000 pages:
# 1. Extract and chunk in batches of 100 pages
# 2. Generate embeddings in parallel
# 3. Upsert to vector DB incrementally
# 4. Show progress to user
```

---

## FastAgent + FastAPI Integration

### How It Works

The architecture combines FastAgent's agent framework with FastAPI's REST API capabilities:

1. **FastAPI Layer** (src/api/main.py):
   - Receives HTTP requests from Gradio frontend
   - Validates request data with Pydantic models
   - Manages session state and authentication
   - Calls FastAgent agents programmatically
   - Returns formatted responses to frontend

2. **FastAgent Layer** (src/agents/):
   - Orchestrator agent initialized with Ollama config
   - Sub-agents defined as tools/workflows
   - All agents use `generic.model_name:tag` format
   - Agents communicate via MCP protocol internally
   - Results passed back to FastAPI

3. **Communication Flow**:
   ```
   Gradio UI → FastAPI endpoint → FastAgent orchestrator
                                         ↓ (MCP tools)
                                   Sub-agents (analyst, search, RAG)
                                         ↓ (via Ollama)
                                   Local LLM responses
                                         ↓
   Gradio UI ← FastAPI response ← Agent results formatted
   ```

### Example Integration Code

```python
# src/api/main.py
from fastapi import FastAPI, HTTPException
from fastagent import Agent
import os

app = FastAPI()

# Initialize FastAgent orchestrator with Ollama
os.environ["GENERIC_API_KEY"] = "ollama"
os.environ["GENERIC_BASE_URL"] = "http://localhost:11434/v1"

orchestrator = Agent(
    name="orchestrator",
    model="generic.llama3.2:latest",
    system_prompt="You are a helpful orchestrator for document Q&A...",
    tools=[analyst_tool, retrieval_tool, web_search_tool]
)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Call FastAgent orchestrator
    response = await orchestrator.run(
        message=request.message,
        context=request.context
    )

    return ChatResponse(
        response=response.content,
        sources=extract_sources(response),
        conversation_id=request.conversation_id
    )
```

---

## REST API Design

### Core Endpoints

#### Chat Endpoints

**POST /api/chat**
```json
// Request
{
  "message": "Who is Aragorn?",
  "conversation_id": "uuid-1234",
  "user_id": "faraday",
  "context": {
    "documents": ["doc_001", "doc_002"],  // optional filter
    "mode": "explanatory"  // or "concise"
  }
}

// Response
{
  "response": "Aragorn is a central character...",
  "sources": [
    {
      "document_id": "doc_001",
      "document_title": "Fellowship of the Ring",
      "page": 42,
      "chunk_id": "doc_001_chunk_042",
      "text": "Aragorn stepped forward...",
      "relevance_score": 0.95
    }
  ],
  "conversation_id": "uuid-1234",
  "agent_used": "orchestrator",
  "processing_time_ms": 1234
}
```

**GET /api/conversations/{conversation_id}**
- Get conversation history

**DELETE /api/conversations/{conversation_id}**
- Clear conversation

#### Document Endpoints

**GET /api/documents**
```json
// Response
{
  "documents": [
    {
      "id": "doc_001",
      "title": "Fellowship of the Ring",
      "filename": "fellowship.pdf",
      "pages": 432,
      "processed_date": "2025-01-15T14:23:01Z",
      "chunks": 284,
      "images": 23,
      "status": "processed"
    }
  ]
}
```

**GET /api/documents/{id}**
- Get document details and content

**GET /api/documents/{id}/content**
- Get markdown or text content
- Query param: `?format=markdown|text`

**POST /api/documents/upload**
- Upload new PDF
- Returns processing job ID

**GET /api/documents/{id}/images**
- Get extracted images list

#### Search Endpoints

**POST /api/search**
```json
// Request
{
  "query": "locations visited by Aragorn",
  "filters": {
    "documents": ["doc_001"],
    "entity_type": "location"
  },
  "limit": 10
}

// Response
{
  "results": [
    {
      "chunk_id": "...",
      "text": "...",
      "score": 0.95,
      "metadata": {...}
    }
  ]
}
```

#### Analytics Endpoints

**GET /api/analytics/popular-queries**
- Most popular queries

**GET /api/analytics/metrics**
- System metrics

#### Health Endpoint

**GET /api/health**
```json
{
  "status": "healthy",
  "ollama": "connected",
  "vector_db": "healthy",
  "models_loaded": ["llama3:8b", "mistral:7b"],
  "documents_indexed": 47
}
```

---

## Frontend Design (Gradio)

### Layout

```python
import gradio as gr

with gr.Blocks(theme=gr.themes.Soft()) as app:
    gr.Markdown("# Buddharauer - AI Document Explorer")

    with gr.Row():
        # Left: Chat Interface
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(
                label="Chat with Documents",
                height=600,
                show_copy_button=True
            )
            msg = gr.Textbox(
                label="Ask a question",
                placeholder="Who is Aragorn?",
                lines=2
            )
            with gr.Row():
                submit = gr.Button("Send")
                clear = gr.Button("Clear")

        # Right: Document Viewer
        with gr.Column(scale=1):
            doc_selector = gr.Dropdown(
                label="Select Document",
                choices=[],  # Populated from API
                interactive=True
            )
            doc_viewer = gr.Markdown(
                label="Document Content",
                height=600
            )
            sources = gr.JSON(
                label="Sources",
                visible=True
            )

    # Event handlers
    submit.click(
        fn=chat,
        inputs=[msg, chatbot],
        outputs=[chatbot, sources]
    )

    doc_selector.change(
        fn=load_document,
        inputs=[doc_selector],
        outputs=[doc_viewer]
    )
```

---

## Testing Strategy

### Test Structure

```
tests/
├── unit/
│   ├── test_chunking.py
│   ├── test_embeddings.py
│   ├── test_agents.py
│   └── test_models.py
├── integration/
│   ├── test_api.py
│   ├── test_pipeline.py
│   └── test_rag.py
├── e2e/
│   └── test_chat_flow.py
└── conftest.py  # Fixtures
```

### Critical Services to Test

#### 1. PDF Processing & Chunking
```python
# tests/unit/test_chunking.py
def test_chunk_large_pdf():
    pdf = load_test_pdf("large_1000_pages.pdf")
    chunks = chunk_document(pdf, strategy="semantic")

    assert len(chunks) > 0
    assert all(chunk["size"] <= MAX_CHUNK_SIZE for chunk in chunks)
    assert all(chunk["overlap"] >= MIN_OVERLAP for chunk in chunks[1:])

def test_chunk_metadata():
    chunks = chunk_document(test_pdf)
    chunk = chunks[0]

    assert "chunk_id" in chunk
    assert "page_start" in chunk
    assert "page_end" in chunk
    assert "chapter" in chunk
```

#### 2. Vector DB Operations
```python
# tests/integration/test_vector_db.py
def test_insert_and_retrieve():
    db = get_vector_db()
    chunk = create_test_chunk()

    db.insert(chunk)
    results = db.search("test query", limit=5)

    assert len(results) > 0
    assert results[0]["score"] > 0.5
```

#### 3. Agent Responses
```python
# tests/integration/test_agents.py
@pytest.mark.asyncio
async def test_orchestrator_agent():
    agent = get_orchestrator_agent()
    response = await agent.process("Who is Aragorn?")

    assert response is not None
    assert len(response["sources"]) > 0
    assert response["agent_used"] == "orchestrator"

@pytest.mark.asyncio
async def test_analyst_agent():
    agent = get_analyst_agent()
    response = await agent.summarize_character("Aragorn")

    assert "identity" in response.lower()
    assert "role" in response.lower()
```

#### 4. REST API
```python
# tests/integration/test_api.py
def test_chat_endpoint(client):
    response = client.post("/api/chat", json={
        "message": "Who is Aragorn?",
        "conversation_id": "test-123"
    })

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "sources" in data

def test_document_upload(client):
    with open("test.pdf", "rb") as f:
        response = client.post("/api/documents/upload", files={"file": f})

    assert response.status_code == 202
    assert "job_id" in response.json()
```

---

## Implementation Summary

### Key Changes from V1

| Aspect | V1 | V2 |
|--------|----|----|
| **Framework** | FastAgent (CLI) | FastAgent + FastAPI + Ollama |
| **Models** | Cloud (Claude, GPT) | Local (Ollama) |
| **Interface** | CLI | Web (Gradio) |
| **UX** | Terminal Q&A | Chat + Document Viewer |
| **Agents** | 5 agents | 4 agents (Orchestrator, Analyst, Web Search, Retrieval) |
| **Deployment** | Local CLI | Local server + web UI |
| **Configuration** | .env | config.yaml + .env |

### Migration Notes

- **Keep**: FastAgent framework (v0.3.17+, Python 3.13.5+)
- **Add**: FastAPI (REST layer), Gradio (UI), Ollama (local models)
- **Keep**: ChromaDB/Qdrant, PyMuPDF, image processing, authentication (optional)
- **Update**: FastAgent configuration to use Ollama via generic provider
- **New**: REST API layer wrapping FastAgent, Gradio frontend, fastagent.config.yaml

---

*Last updated: 2025-11-05*
*Architecture Version: 2.0*
*Next: Update all specification documents and create implementation plan*
