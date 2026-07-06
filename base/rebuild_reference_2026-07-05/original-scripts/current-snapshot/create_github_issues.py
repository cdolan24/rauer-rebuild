#!/usr/bin/env python3
"""
Create GitHub Issues from Implementation Plan

This script creates all 36 GitHub issues from IMPLEMENTATION_PLAN.md
using the GitHub REST API.

Usage:
    python scripts/create_github_issues.py

Requirements:
    - requests library: pip install requests
    - GitHub Personal Access Token with repo scope
    - Set GITHUB_TOKEN environment variable
"""

import sys
from github_utils import (
    get_github_token,
    batch_create_issues,
    print_summary,
    GITHUB_OWNER,
    GITHUB_REPO
)


# Define all 36 issues from IMPLEMENTATION_PLAN.md
ISSUES = [
    # Phase 0: Environment Setup
    {
        "title": "Phase 0: Setup Ollama and pull models",
        "body": """**Phase**: 0 - Environment Setup
**Priority**: High
**Estimated Time**: 2 hours

**Description**:
Install Ollama and pull all required models for FastAgent integration.

**Tasks**:
- [ ] Download and install Ollama from https://ollama.ai/
- [ ] Pull llama3.2:latest (orchestrator, analyst)
- [ ] Pull qwen2.5:latest (alternative, better tool calling)
- [ ] Pull mistral:7b (web search)
- [ ] Pull nomic-embed-text (embeddings)
- [ ] Verify installation: `ollama list`
- [ ] Test Ollama API: `curl http://localhost:11434/api/generate`

**Acceptance Criteria**:
- [ ] Ollama installed and running
- [ ] All 4 models pulled and available
- [ ] Ollama API responding correctly
- [ ] Models tested with basic prompts

**Technical Details**:
- Models total size: ~10-15 GB
- Requires GPU recommended (CPU works but slower)
- FastAgent requires Python 3.13.5+

**Testing**:
- [ ] Manual verification of model responses
- [ ] Test embeddings generation

**Labels**: `phase-0`, `setup`, `priority-high`
""",
        "labels": ["phase-0", "setup", "priority-high"]
    },
    {
        "title": "Phase 0: Create project structure and dependencies",
        "body": """**Phase**: 0 - Environment Setup
**Priority**: High
**Estimated Time**: 3 hours

**Description**:
Set up Python environment, project structure, and install core dependencies.

**Tasks**:
- [ ] Ensure Python 3.13.5+ installed
- [ ] Create project directory structure
- [ ] Create requirements.txt with all dependencies
- [ ] Install FastAgent: `uv pip install fast-agent-mcp>=0.3.17`
- [ ] Install FastAPI, Gradio, ChromaDB
- [ ] Install testing dependencies (pytest, httpx)
- [ ] Setup git repository with .gitignore
- [ ] Create virtual environment

**Acceptance Criteria**:
- [ ] Python 3.13.5+ verified
- [ ] All directories created (src/, tests/, data/, etc.)
- [ ] All dependencies installed successfully
- [ ] Virtual environment activated
- [ ] Git repository initialized

**Technical Details**:
- Directory structure:
  - src/{api,agents,pipeline,database,frontend,utils}
  - tests/{unit,integration,e2e}
  - data, processed, vector_db, data_storage, scripts
- FastAgent v0.3.17+ required for MCP support
- Use uv or pip for package management

**Testing**:
- [ ] Import all major packages successfully
- [ ] Run `python --version` to verify Python 3.13.5+

**Labels**: `phase-0`, `setup`, `priority-high`
""",
        "labels": ["phase-0", "setup", "priority-high"]
    },
    {
        "title": "Phase 0: Implement configuration system",
        "body": """**Phase**: 0 - Environment Setup
**Priority**: High
**Estimated Time**: 4 hours

**Description**:
Create configuration system with YAML files and environment variable support.

**Tasks**:
- [ ] Create `src/utils/config.py` - YAML config loader
- [ ] Create `config.example.yaml` - Application config template
- [ ] Create `fastagent.config.example.yaml` - FastAgent provider config
- [ ] Add environment variable override support
- [ ] Create `.env.example` with all required variables
- [ ] Update .gitignore to exclude actual config files
- [ ] Add validation for required config values

**Acceptance Criteria**:
- [ ] Config loader reads YAML files
- [ ] Environment variables override YAML values
- [ ] Example configs documented with comments
- [ ] Validation raises clear errors for missing values
- [ ] Actual config files gitignored

**Technical Details**:
Files to create:
- `src/utils/config.py`: ConfigLoader class
- `config.example.yaml`: App settings (agents, vector DB, etc.)
- `fastagent.config.example.yaml`: Ollama generic provider config
- `.env.example`: Environment variable template

Config structure:
```yaml
fastagent:
  provider: "generic"
  ollama_base_url: "http://localhost:11434"
agents:
  orchestrator:
    model: "generic.llama3.2:latest"
    temperature: 0.7
```

**Testing**:
- [ ] Unit tests for config loader
- [ ] Test environment variable overrides
- [ ] Test validation errors

**Labels**: `phase-0`, `setup`, `priority-high`
""",
        "labels": ["phase-0", "setup", "priority-high"]
    },
    {
        "title": "Phase 0: Verify Ollama + FastAgent integration",
        "body": """**Phase**: 0 - Environment Setup
**Priority**: High
**Estimated Time**: 3 hours

**Description**:
Verify that FastAgent can connect to Ollama using the generic provider.

**Tasks**:
- [ ] Configure fastagent.config.yaml with Ollama endpoint
- [ ] Set up environment variables (GENERIC_API_KEY, GENERIC_BASE_URL)
- [ ] Test FastAgent setup: `fast-agent setup`
- [ ] Verify model responses: `fast-agent --model generic.llama3.2:latest`
- [ ] Test embeddings generation via Ollama API
- [ ] Confirm tool calling works with Ollama models
- [ ] Create test script for verification

**Acceptance Criteria**:
- [ ] FastAgent successfully connects to Ollama
- [ ] Models respond to prompts via FastAgent
- [ ] Embeddings generated correctly
- [ ] Tool calling works (test with simple tool)
- [ ] No API errors or connection issues

**Technical Details**:
Configuration:
```yaml
# fastagent.config.yaml
generic:
  api_key: "ollama"
  base_url: "http://localhost:11434/v1"
```

Environment variables:
```bash
export GENERIC_API_KEY="ollama"
export GENERIC_BASE_URL="http://localhost:11434/v1"
```

Test script should verify:
- Connection to Ollama
- Model inference
- Embedding generation
- Tool calling capability

**Testing**:
- [ ] Manual testing with fast-agent CLI
- [ ] Python test script for API calls
- [ ] Verify all models respond correctly

**Labels**: `phase-0`, `setup`, `priority-high`
""",
        "labels": ["phase-0", "setup", "priority-high"]
    },

    # Phase 1: Document Processing Pipeline
    {
        "title": "Phase 1: Implement PDF text extraction",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Create PDF text extraction module using PyMuPDF with metadata extraction.

**Tasks**:
- [ ] Create `src/pipeline/pdf_extractor.py`
- [ ] Implement text extraction with PyMuPDF
- [ ] Extract metadata (pages, title, author, etc.)
- [ ] Handle large PDFs with progress tracking
- [ ] Add error handling for corrupted PDFs
- [ ] Support image extraction (optional)

**Acceptance Criteria**:
- [ ] Extract text from PDF files
- [ ] Preserve page numbers and structure
- [ ] Extract metadata correctly
- [ ] Progress tracking for large files
- [ ] Graceful error handling
- [ ] Tests passing

**Technical Details**:
File: `src/pipeline/pdf_extractor.py`

Key functions:
- `extract_text_from_pdf(file_path: str) -> Dict`
- `extract_metadata(file_path: str) -> Dict`
- `extract_page_text(pdf_doc, page_num: int) -> str`

Dependencies:
- PyMuPDF (fitz)
- python-dotenv

**Testing**:
- [ ] Unit tests with sample PDFs
- [ ] Test with MalifauxStories PDFs from data/
- [ ] Test error handling with corrupted files
- [ ] Performance test with large PDFs

**Labels**: `phase-1`, `pipeline`, `priority-high`
""",
        "labels": ["phase-1", "pipeline", "priority-high"]
    },
    {
        "title": "Phase 1: Create semantic chunking system",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Estimated Time**: 8 hours

**Description**:
Implement semantic chunking for PDF text with configurable size and overlap.

**Tasks**:
- [ ] Create `src/pipeline/chunker.py`
- [ ] Implement semantic chunking algorithm
- [ ] Configurable chunk size and overlap (800 tokens, 150 overlap)
- [ ] Metadata enrichment (page numbers, chapter info)
- [ ] Handle edge cases (tables, lists, code blocks)
- [ ] Preserve document structure

**Acceptance Criteria**:
- [ ] Text chunked with semantic boundaries
- [ ] Configurable chunk size and overlap
- [ ] Metadata preserved in chunks
- [ ] Edge cases handled correctly
- [ ] Tests passing

**Technical Details**:
File: `src/pipeline/chunker.py`

Key functions:
- `chunk_text(text: str, chunk_size: int, overlap: int) -> List[DocumentChunk]`
- `semantic_split(text: str) -> List[str]`
- `enrich_metadata(chunk: str, metadata: Dict) -> DocumentChunk`

Use LangChain TextSplitter or implement custom splitter:
- RecursiveCharacterTextSplitter
- Sentence-based splitting
- Preserve paragraphs and sections

**Testing**:
- [ ] Unit tests for chunking logic
- [ ] Test with various chunk sizes
- [ ] Test metadata enrichment
- [ ] Test edge cases (tables, lists)

**Labels**: `phase-1`, `pipeline`, `priority-high`
""",
        "labels": ["phase-1", "pipeline", "priority-high"]
    },
    {
        "title": "Phase 1: Setup Ollama embeddings generation",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Estimated Time**: 5 hours

**Description**:
Create embeddings generation module using Ollama's nomic-embed-text model.

**Tasks**:
- [ ] Create `src/pipeline/embeddings.py`
- [ ] Use Ollama embeddings API (nomic-embed-text)
- [ ] Implement batch processing for efficiency
- [ ] Add progress tracking for large documents
- [ ] Cache embeddings for reuse
- [ ] Handle API errors and retries

**Acceptance Criteria**:
- [ ] Generate embeddings via Ollama
- [ ] Batch processing implemented
- [ ] Progress tracking working
- [ ] Error handling and retries
- [ ] Tests passing

**Technical Details**:
File: `src/pipeline/embeddings.py`

Key functions:
- `generate_embedding(text: str) -> List[float]`
- `batch_generate_embeddings(texts: List[str]) -> List[List[float]]`
- `embed_chunks(chunks: List[DocumentChunk]) -> List[EmbeddedChunk]`

Ollama API call:
```python
import requests
response = requests.post(
    "http://localhost:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": text}
)
embedding = response.json()["embedding"]
```

**Testing**:
- [ ] Unit tests for embedding generation
- [ ] Test batch processing
- [ ] Test error handling and retries
- [ ] Performance benchmarks

**Labels**: `phase-1`, `pipeline`, `priority-high`
""",
        "labels": ["phase-1", "pipeline", "priority-high"]
    },
    {
        "title": "Phase 1: Integrate ChromaDB vector store",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Set up ChromaDB vector store for storing and searching embeddings.

**Tasks**:
- [ ] Create `src/database/vector_store.py`
- [ ] Initialize ChromaDB collection
- [ ] Implement upsert for chunks with metadata
- [ ] Create search interface (semantic search)
- [ ] Add filtering by metadata
- [ ] Configure persistence to disk

**Acceptance Criteria**:
- [ ] ChromaDB initialized and persisted
- [ ] Chunks upserted with embeddings and metadata
- [ ] Search returns relevant results
- [ ] Metadata filtering works
- [ ] Tests passing

**Technical Details**:
File: `src/database/vector_store.py`

Key functions:
- `initialize_vector_store(persist_directory: str) -> Collection`
- `upsert_chunks(chunks: List[EmbeddedChunk]) -> None`
- `search(query_embedding: List[float], top_k: int) -> List[SearchResult]`
- `search_with_filter(query: str, metadata_filter: Dict) -> List[SearchResult]`

ChromaDB setup:
```python
import chromadb
client = chromadb.PersistentClient(path="vector_db/")
collection = client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)
```

**Testing**:
- [ ] Unit tests for vector operations
- [ ] Test search relevance
- [ ] Test metadata filtering
- [ ] Test persistence

**Labels**: `phase-1`, `database`, `priority-high`
""",
        "labels": ["phase-1", "database", "priority-high"]
    },
    {
        "title": "Phase 1: Create document registry",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: Medium
**Estimated Time**: 4 hours

**Description**:
Create SQLite database for tracking document processing status.

**Tasks**:
- [ ] Create `src/database/document_registry.py`
- [ ] Design schema for documents and processing status
- [ ] Implement CRUD operations
- [ ] Track processing timestamps and errors
- [ ] Link documents to vector DB chunks
- [ ] Add migration support

**Acceptance Criteria**:
- [ ] SQLite database created
- [ ] Document tracking working
- [ ] Processing status tracked
- [ ] Error logging implemented
- [ ] Tests passing

**Technical Details**:
File: `src/database/document_registry.py`

Schema:
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    file_hash TEXT,
    status TEXT,  -- pending, processing, completed, failed
    processed_at TIMESTAMP,
    error_message TEXT,
    metadata JSON
);

CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT,
    vector_id TEXT,  -- Link to ChromaDB
    page_start INTEGER,
    page_end INTEGER,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);
```

**Testing**:
- [ ] Unit tests for CRUD operations
- [ ] Test status tracking
- [ ] Test error logging

**Labels**: `phase-1`, `database`, `priority-medium`
""",
        "labels": ["phase-1", "database", "priority-medium"]
    },
    {
        "title": "Phase 1: Build processing script with CLI",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Estimated Time**: 5 hours

**Description**:
Create CLI script for processing PDFs with batch and single-file modes.

**Tasks**:
- [ ] Create `scripts/process_documents.py`
- [ ] Implement CLI with argparse/click
- [ ] Support single file and batch processing
- [ ] Add progress bars (tqdm)
- [ ] Error reporting and logging
- [ ] Dry-run mode for testing

**Acceptance Criteria**:
- [ ] CLI accepts file paths or directories
- [ ] Progress bars show processing status
- [ ] Errors logged and displayed
- [ ] Dry-run mode works
- [ ] Tests passing

**Technical Details**:
File: `scripts/process_documents.py`

CLI interface:
```bash
# Process single file
python scripts/process_documents.py data/sample.pdf

# Process directory
python scripts/process_documents.py data/ --recursive

# Batch processing
python scripts/process_documents.py --batch data/*.pdf

# Dry run
python scripts/process_documents.py data/ --dry-run
```

Workflow:
1. Extract text from PDF
2. Chunk text semantically
3. Generate embeddings
4. Upsert to vector store
5. Update document registry

**Testing**:
- [ ] Integration test with sample PDFs
- [ ] Test MalifauxStories PDFs from data/
- [ ] Test error handling
- [ ] Test dry-run mode

**Labels**: `phase-1`, `pipeline`, `priority-high`
""",
        "labels": ["phase-1", "pipeline", "priority-high"]
    },

    # Phase 2: FastAPI Backend
    {
        "title": "Phase 2: Setup FastAPI application structure",
        "body": """**Phase**: 2 - FastAPI Backend
**Priority**: High
**Estimated Time**: 5 hours

**Description**:
Create FastAPI application foundation with middleware and error handling.

**Tasks**:
- [ ] Create `src/api/main.py` - FastAPI app
- [ ] Configure CORS for Gradio
- [ ] Add error handling middleware
- [ ] Create Pydantic request/response models
- [ ] Setup logging
- [ ] Add startup/shutdown events

**Acceptance Criteria**:
- [ ] FastAPI app starts successfully
- [ ] CORS configured correctly
- [ ] Error handling middleware working
- [ ] Request/response validation working
- [ ] Tests passing

**Technical Details**:
File: `src/api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Buddharauer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Gradio frontend
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.on_event("startup")
async def startup():
    # Initialize FastAgent, vector store, etc.
    pass
```

**Testing**:
- [ ] Integration tests for API startup
- [ ] Test CORS headers
- [ ] Test error handling

**Labels**: `phase-2`, `backend`, `priority-high`
""",
        "labels": ["phase-2", "backend", "priority-high"]
    },
    {
        "title": "Phase 2: Implement chat endpoint",
        "body": """**Phase**: 2 - FastAPI Backend
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Create chat endpoint for conversational Q&A.

**Tasks**:
- [ ] Create `src/api/routes/chat.py`
- [ ] Implement POST /api/chat endpoint
- [ ] Implement GET /api/conversations/{id} endpoint
- [ ] Implement DELETE /api/conversations/{id} endpoint
- [ ] Add conversation context management
- [ ] Add streaming response support (optional)

**Acceptance Criteria**:
- [ ] Chat endpoint accepts messages
- [ ] Conversation history retrieved
- [ ] Conversations can be deleted
- [ ] Context managed correctly
- [ ] Tests passing

**Technical Details**:
File: `src/api/routes/chat.py`

Endpoints:
```python
@router.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    # Call FastAgent orchestrator
    # Return response with sources
    pass

@router.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> Conversation:
    # Retrieve conversation history
    pass

@router.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    # Clear conversation
    pass
```

**Testing**:
- [ ] Integration tests for chat flow
- [ ] Test conversation management
- [ ] Test context handling

**Labels**: `phase-2`, `backend`, `priority-high`
""",
        "labels": ["phase-2", "backend", "priority-high"]
    },
    {
        "title": "Phase 2: Implement document endpoints",
        "body": """**Phase**: 2 - FastAPI Backend
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Create endpoints for document management and retrieval.

**Tasks**:
- [ ] Create `src/api/routes/documents.py`
- [ ] Implement GET /api/documents (list all)
- [ ] Implement GET /api/documents/{id} (get metadata)
- [ ] Implement GET /api/documents/{id}/content (get content)
- [ ] Implement POST /api/documents/upload (upload PDF)
- [ ] Add pagination for document list

**Acceptance Criteria**:
- [ ] All endpoints implemented
- [ ] Document upload works
- [ ] Content retrieval works
- [ ] Pagination works
- [ ] Tests passing

**Technical Details**:
File: `src/api/routes/documents.py`

Endpoints:
```python
@router.get("/api/documents")
async def list_documents(skip: int = 0, limit: int = 20) -> List[Document]:
    # List documents with pagination
    pass

@router.get("/api/documents/{document_id}")
async def get_document(document_id: str) -> Document:
    # Get document metadata
    pass

@router.get("/api/documents/{document_id}/content")
async def get_document_content(document_id: str) -> DocumentContent:
    # Get full document content
    pass

@router.post("/api/documents/upload")
async def upload_document(file: UploadFile) -> Document:
    # Upload and process PDF
    pass
```

**Testing**:
- [ ] Integration tests for all endpoints
- [ ] Test file upload
- [ ] Test pagination

**Labels**: `phase-2`, `backend`, `priority-high`
""",
        "labels": ["phase-2", "backend", "priority-high"]
    },
    {
        "title": "Phase 2: Create query logger",
        "body": """**Phase**: 2 - FastAPI Backend
**Priority**: Medium
**Estimated Time**: 4 hours

**Description**:
Implement query logging to SQLite for analytics and debugging.

**Tasks**:
- [ ] Create `src/database/query_logger.py`
- [ ] Design schema for query logs
- [ ] Log all queries with timestamps
- [ ] Track response times
- [ ] Add user tracking (optional)
- [ ] Create analytics queries

**Acceptance Criteria**:
- [ ] Queries logged to SQLite
- [ ] Response times tracked
- [ ] Analytics queries working
- [ ] Tests passing

**Technical Details**:
File: `src/database/query_logger.py`

Schema:
```sql
CREATE TABLE query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query TEXT NOT NULL,
    response TEXT,
    response_time_ms INTEGER,
    conversation_id TEXT,
    user_id TEXT,
    sources_used TEXT,  -- JSON array
    error TEXT
);
```

**Testing**:
- [ ] Unit tests for logging
- [ ] Test analytics queries

**Labels**: `phase-2`, `backend`, `priority-medium`
""",
        "labels": ["phase-2", "backend", "priority-medium"]
    },
    {
        "title": "Phase 2: Add API tests",
        "body": """**Phase**: 2 - FastAPI Backend
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Create comprehensive integration tests for all API endpoints.

**Tasks**:
- [ ] Create `tests/integration/test_api.py`
- [ ] Create `tests/integration/test_endpoints.py`
- [ ] Test all chat endpoints
- [ ] Test all document endpoints
- [ ] Test error handling
- [ ] Test authentication (if implemented)

**Acceptance Criteria**:
- [ ] All endpoints tested
- [ ] Edge cases covered
- [ ] Error handling tested
- [ ] >80% coverage for API routes
- [ ] Tests passing

**Technical Details**:
Files:
- `tests/integration/test_api.py` - API foundation tests
- `tests/integration/test_endpoints.py` - Endpoint-specific tests

Use httpx.AsyncClient for testing:
```python
from httpx import AsyncClient
from src.api.main import app

async def test_chat_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "test"})
        assert response.status_code == 200
```

**Testing**:
- [ ] Run full test suite
- [ ] Check coverage report
- [ ] CI/CD integration (optional)

**Labels**: `phase-2`, `backend`, `testing`, `priority-high`
""",
        "labels": ["phase-2", "backend", "testing", "priority-high"]
    },

    # Phase 3: FastAgent Agents Implementation
    {
        "title": "Phase 3: Setup FastAgent with Ollama generic provider",
        "body": """**Phase**: 3 - FastAgent Agents Implementation
**Priority**: High
**Estimated Time**: 5 hours

**Description**:
Configure FastAgent to use Ollama local models via generic provider.

**Tasks**:
- [ ] Install fast-agent-mcp v0.3.17+
- [ ] Create fastagent.config.yaml with Ollama endpoint
- [ ] Set up environment variables (GENERIC_API_KEY, GENERIC_BASE_URL)
- [ ] Create `src/utils/fastagent_client.py` wrapper
- [ ] Test basic FastAgent + Ollama connectivity
- [ ] Document configuration for team

**Acceptance Criteria**:
- [ ] FastAgent connects to Ollama successfully
- [ ] Configuration documented
- [ ] Wrapper utilities working
- [ ] Tests passing

**Technical Details**:
Files:
- `fastagent.config.yaml`: Ollama generic provider config
- `src/utils/fastagent_client.py`: FastAgent wrapper utilities

Configuration:
```yaml
# fastagent.config.yaml
generic:
  api_key: "ollama"
  base_url: "http://localhost:11434/v1"
```

Wrapper example:
```python
from fastagent import Agent
import os

os.environ["GENERIC_API_KEY"] = "ollama"
os.environ["GENERIC_BASE_URL"] = "http://localhost:11434/v1"

def create_agent(name: str, model: str, system_prompt: str, tools: list):
    return Agent(name=name, model=model, system_prompt=system_prompt, tools=tools)
```

**Testing**:
- [ ] Unit tests for FastAgent wrapper
- [ ] Integration test with Ollama
- [ ] Test all configured models

**Labels**: `phase-3`, `agents`, `priority-high`
""",
        "labels": ["phase-3", "agents", "priority-high"]
    },
    {
        "title": "Phase 3: Implement RAG retrieval agent (FastAgent)",
        "body": """**Phase**: 3 - FastAgent Agents Implementation
**Priority**: High
**Estimated Time**: 8 hours

**Description**:
Create RAG retrieval agent using FastAgent with vector DB access.

**Tasks**:
- [ ] Create `src/agents/retrieval.py`
- [ ] Define as FastAgent tool or sub-agent
- [ ] Create MCP tool for vector DB access
- [ ] Use generic.qwen2.5:latest for query reformulation
- [ ] Implement semantic search with ChromaDB
- [ ] Return chunks with citations

**Acceptance Criteria**:
- [ ] Retrieval agent returns relevant chunks
- [ ] Citations included in results
- [ ] Query reformulation working
- [ ] MCP tool properly integrated
- [ ] Tests passing

**Technical Details**:
File: `src/agents/retrieval.py`

Agent setup:
```python
from fastagent import Agent

retrieval_agent = Agent(
    name="retrieval",
    model="generic.qwen2.5:latest",
    system_prompt="You are a retrieval specialist...",
    tools=[vector_search_tool]
)
```

MCP tool for vector search:
```python
def vector_search_tool(query: str, top_k: int = 5) -> List[Dict]:
    """Search vector database for relevant chunks."""
    # Query reformulation
    # Semantic search
    # Return with citations
    pass
```

**Testing**:
- [ ] Unit tests for retrieval logic
- [ ] Integration tests with vector DB
- [ ] Test query reformulation
- [ ] Test citation generation

**Labels**: `phase-3`, `agents`, `rag`, `priority-high`
""",
        "labels": ["phase-3", "agents", "rag", "priority-high"]
    },
    {
        "title": "Phase 3: Implement orchestrator agent (FastAgent)",
        "body": """**Phase**: 3 - FastAgent Agents Implementation
**Priority**: High
**Estimated Time**: 8 hours

**Description**:
Create main orchestrator agent that routes to sub-agents.

**Tasks**:
- [ ] Create `src/agents/orchestrator.py`
- [ ] Use generic.llama3.2:latest model
- [ ] Define tools for sub-agents (analyst, retrieval, web_search)
- [ ] Manage conversation context via FastAgent memory
- [ ] Implement intent-based routing
- [ ] Format responses with source citations

**Acceptance Criteria**:
- [ ] Orchestrator routes to correct sub-agents
- [ ] Conversation context maintained
- [ ] Source citations formatted correctly
- [ ] Intent recognition working
- [ ] Tests passing

**Technical Details**:
File: `src/agents/orchestrator.py`

Agent setup:
```python
from fastagent import Agent

orchestrator = Agent(
    name="orchestrator",
    model="generic.llama3.2:latest",
    system_prompt="You are a helpful orchestrator for document Q&A...",
    tools=[analyst_tool, retrieval_tool, web_search_tool]
)
```

Intent routing:
- Document questions → retrieval_tool
- Analysis/summary → analyst_tool
- External info → web_search_tool

**Testing**:
- [ ] Unit tests for routing logic
- [ ] Integration tests with sub-agents
- [ ] Test conversation context
- [ ] Test citation formatting

**Labels**: `phase-3`, `agents`, `orchestrator`, `priority-high`
""",
        "labels": ["phase-3", "agents", "orchestrator", "priority-high"]
    },
    {
        "title": "Phase 3: Implement analyst agent (FastAgent)",
        "body": """**Phase**: 3 - FastAgent Agents Implementation
**Priority**: Medium
**Estimated Time**: 6 hours

**Description**:
Create analyst sub-agent for summarization and creative analysis.

**Tasks**:
- [ ] Create `src/agents/analyst.py`
- [ ] Use generic.llama3.2:latest or generic.qwen2.5:latest
- [ ] Implement summarization
- [ ] Implement entity extraction
- [ ] Provide creative insights (for Faraday profile)
- [ ] Generate explanatory responses

**Acceptance Criteria**:
- [ ] Analyst generates summaries
- [ ] Entity extraction working
- [ ] Creative insights provided
- [ ] Responses formatted correctly
- [ ] Tests passing

**Technical Details**:
File: `src/agents/analyst.py`

Agent setup:
```python
from fastagent import Agent

analyst = Agent(
    name="analyst",
    model="generic.llama3.2:latest",
    system_prompt="You are an analytical assistant specializing in...",
    tools=[]
)
```

Capabilities:
- Summarize document sections
- Extract entities (people, places, events)
- Provide creative interpretations
- Explain complex topics simply (Faraday profile)

**Testing**:
- [ ] Unit tests for analysis functions
- [ ] Test summarization quality
- [ ] Test entity extraction
- [ ] Test creative insights

**Labels**: `phase-3`, `agents`, `analyst`, `priority-medium`
""",
        "labels": ["phase-3", "agents", "analyst", "priority-medium"]
    },
    {
        "title": "Phase 3: Implement web search agent (FastAgent)",
        "body": """**Phase**: 3 - FastAgent Agents Implementation
**Priority**: Medium
**Estimated Time**: 7 hours

**Description**:
Create web search sub-agent with MCP web search tools.

**Tasks**:
- [ ] Create `src/agents/web_search.py`
- [ ] Use generic.mistral:7b for fast summarization
- [ ] Integrate with DuckDuckGo MCP server (or similar)
- [ ] Implement query formulation
- [ ] Implement result summarization
- [ ] Combine with document context

**Acceptance Criteria**:
- [ ] Web search returns relevant results
- [ ] Query formulation working
- [ ] Result summarization working
- [ ] Combined with document context
- [ ] Tests passing

**Technical Details**:
File: `src/agents/web_search.py`

Agent setup:
```python
from fastagent import Agent

web_search = Agent(
    name="web_search",
    model="generic.mistral:7b",
    system_prompt="You are a web search specialist...",
    tools=[duckduckgo_search_tool]
)
```

MCP tool integration:
- Install DuckDuckGo MCP server
- Configure in fastagent.config.yaml
- Use tool for web searches

**Testing**:
- [ ] Unit tests for search logic
- [ ] Integration tests with MCP server
- [ ] Test query formulation
- [ ] Test result summarization

**Labels**: `phase-3`, `agents`, `web-search`, `priority-medium`
""",
        "labels": ["phase-3", "agents", "web-search", "priority-medium"]
    },
    {
        "title": "Phase 3: Integrate FastAgent with FastAPI endpoints",
        "body": """**Phase**: 3 - FastAgent Agents Implementation
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Connect FastAgent orchestrator to FastAPI chat endpoint.

**Tasks**:
- [ ] Update `src/api/routes/chat.py` to call FastAgent
- [ ] Initialize orchestrator on app startup
- [ ] Handle async calls to agents
- [ ] Extract sources from agent responses
- [ ] Format responses for frontend
- [ ] Add error handling for agent failures

**Acceptance Criteria**:
- [ ] Chat endpoint calls FastAgent orchestrator
- [ ] Agent responses formatted correctly
- [ ] Sources extracted and included
- [ ] Error handling working
- [ ] Tests passing

**Technical Details**:
File: `src/api/routes/chat.py`

Integration:
```python
from src.agents.orchestrator import orchestrator

@router.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    # Call FastAgent orchestrator
    response = await orchestrator.run(
        message=request.message,
        context=request.context
    )

    # Extract sources
    sources = extract_sources(response)

    return ChatResponse(
        response=response.content,
        sources=sources,
        conversation_id=request.conversation_id
    )
```

**Testing**:
- [ ] Integration tests for FastAPI + FastAgent
- [ ] Test agent routing
- [ ] Test source extraction
- [ ] Test error handling

**Labels**: `phase-3`, `agents`, `backend`, `priority-high`
""",
        "labels": ["phase-3", "agents", "backend", "priority-high"]
    },

    # Phase 4: Gradio Frontend
    {
        "title": "Phase 4: Setup Gradio application",
        "body": """**Phase**: 4 - Gradio Frontend
**Priority**: High
**Estimated Time**: 5 hours

**Description**:
Create basic Gradio app structure with layout and theme.

**Tasks**:
- [ ] Create `src/frontend/app.py`
- [ ] Setup basic layout (chat + document viewer)
- [ ] Configure theme
- [ ] Add app title and description
- [ ] Configure Gradio server settings

**Acceptance Criteria**:
- [ ] Gradio app launches successfully
- [ ] Layout displays correctly
- [ ] Theme configured
- [ ] Tests passing (manual)

**Technical Details**:
File: `src/frontend/app.py`

Basic structure:
```python
import gradio as gr

with gr.Blocks(theme=gr.themes.Soft()) as app:
    gr.Markdown("# Buddharauer - Document Q&A")

    with gr.Row():
        with gr.Column(scale=1):
            # Chat interface
            pass
        with gr.Column(scale=1):
            # Document viewer
            pass

app.launch(server_name="0.0.0.0", server_port=7860)
```

**Testing**:
- [ ] Manual testing of UI layout
- [ ] Test on different screen sizes
- [ ] Test theme rendering

**Labels**: `phase-4`, `frontend`, `priority-high`
""",
        "labels": ["phase-4", "frontend", "priority-high"]
    },
    {
        "title": "Phase 4: Create chat component",
        "body": """**Phase**: 4 - Gradio Frontend
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Build chat interface component with history and message formatting.

**Tasks**:
- [ ] Create `src/frontend/components/chat.py`
- [ ] Implement chat interface with history
- [ ] Add message formatting (user vs assistant)
- [ ] Display source citations
- [ ] Add input field and submit button
- [ ] Handle loading states

**Acceptance Criteria**:
- [ ] Chat interface functional
- [ ] Message history displayed
- [ ] Citations displayed correctly
- [ ] Loading states working
- [ ] Tests passing (manual)

**Technical Details**:
File: `src/frontend/components/chat.py`

Components:
```python
import gradio as gr

chatbot = gr.Chatbot(
    label="Chat",
    height=600,
    show_copy_button=True
)

msg_input = gr.Textbox(
    label="Ask a question",
    placeholder="Type your question here...",
    lines=2
)

submit_btn = gr.Button("Send", variant="primary")
```

Message formatting:
- User messages: plain text
- Assistant messages: markdown with citations

**Testing**:
- [ ] Manual testing of chat flow
- [ ] Test message formatting
- [ ] Test citation display

**Labels**: `phase-4`, `frontend`, `priority-high`
""",
        "labels": ["phase-4", "frontend", "priority-high"]
    },
    {
        "title": "Phase 4: Create document viewer component",
        "body": """**Phase**: 4 - Gradio Frontend
**Priority**: High
**Estimated Time**: 7 hours

**Description**:
Build document viewer with citation highlighting and navigation.

**Tasks**:
- [ ] Create `src/frontend/components/document_viewer.py`
- [ ] Implement markdown/text display
- [ ] Add citation highlighting
- [ ] Implement scroll to citation
- [ ] Add page navigation
- [ ] Handle large documents

**Acceptance Criteria**:
- [ ] Document content displayed
- [ ] Citations highlighted
- [ ] Scroll to citation working
- [ ] Page navigation working
- [ ] Tests passing (manual)

**Technical Details**:
File: `src/frontend/components/document_viewer.py`

Components:
```python
import gradio as gr

doc_viewer = gr.Markdown(
    label="Document Viewer",
    height=600
)

page_selector = gr.Slider(
    minimum=1,
    maximum=100,
    step=1,
    label="Page"
)
```

Features:
- Highlight cited text
- Scroll to citation on click
- Navigate by page number
- Display metadata (title, page count)

**Testing**:
- [ ] Manual testing with sample documents
- [ ] Test citation highlighting
- [ ] Test navigation

**Labels**: `phase-4`, `frontend`, `priority-high`
""",
        "labels": ["phase-4", "frontend", "priority-high"]
    },
    {
        "title": "Phase 4: Implement document management UI",
        "body": """**Phase**: 4 - Gradio Frontend
**Priority**: Medium
**Estimated Time**: 5 hours

**Description**:
Create UI for document selection, upload, and status display.

**Tasks**:
- [ ] Add document selector dropdown
- [ ] Implement file upload interface
- [ ] Display processing status
- [ ] Show document metadata
- [ ] Add refresh button
- [ ] Handle upload errors

**Acceptance Criteria**:
- [ ] Document selection working
- [ ] File upload working
- [ ] Processing status displayed
- [ ] Metadata displayed
- [ ] Tests passing (manual)

**Technical Details**:
Components:
```python
import gradio as gr

doc_selector = gr.Dropdown(
    label="Select Document",
    choices=[],
    interactive=True
)

file_upload = gr.File(
    label="Upload PDF",
    file_types=[".pdf"]
)

status_display = gr.Textbox(
    label="Status",
    interactive=False
)
```

**Testing**:
- [ ] Manual testing of document selection
- [ ] Test file upload
- [ ] Test status updates

**Labels**: `phase-4`, `frontend`, `priority-medium`
""",
        "labels": ["phase-4", "frontend", "priority-medium"]
    },
    {
        "title": "Phase 4: Integrate with FastAPI backend",
        "body": """**Phase**: 4 - Gradio Frontend
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Connect Gradio frontend to FastAPI backend endpoints.

**Tasks**:
- [ ] Create `src/frontend/api_client.py`
- [ ] Implement API calls for all endpoints
- [ ] Add WebSocket support for real-time updates (optional)
- [ ] Handle API errors gracefully
- [ ] Add retry logic for failed requests
- [ ] Display user-friendly error messages

**Acceptance Criteria**:
- [ ] All API calls working
- [ ] Error handling implemented
- [ ] User feedback displayed
- [ ] Tests passing

**Technical Details**:
File: `src/frontend/api_client.py`

```python
import httpx

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def chat(self, message: str, conversation_id: str):
        response = await self.client.post(
            f"{self.base_url}/api/chat",
            json={"message": message, "conversation_id": conversation_id}
        )
        return response.json()

    async def list_documents(self):
        response = await self.client.get(f"{self.base_url}/api/documents")
        return response.json()
```

**Testing**:
- [ ] Integration tests with backend
- [ ] Test error handling
- [ ] Test retry logic

**Labels**: `phase-4`, `frontend`, `backend`, `priority-high`
""",
        "labels": ["phase-4", "frontend", "backend", "priority-high"]
    },
    {
        "title": "Phase 4: Polish UI and add error handling",
        "body": """**Phase**: 4 - Gradio Frontend
**Priority**: Medium
**Estimated Time**: 5 hours

**Description**:
Add UI polish, loading states, and comprehensive error handling.

**Tasks**:
- [ ] Add loading spinners
- [ ] Implement error messages and toasts
- [ ] Add responsive design tweaks
- [ ] Customize theme colors and fonts
- [ ] Add keyboard shortcuts
- [ ] Improve accessibility

**Acceptance Criteria**:
- [ ] Loading states displayed
- [ ] Error messages user-friendly
- [ ] Responsive design working
- [ ] Theme customized
- [ ] Tests passing (manual)

**Technical Details**:
Enhancements:
- Loading spinners during API calls
- Toast notifications for errors
- Keyboard shortcuts (Enter to send, etc.)
- Color scheme matching brand
- ARIA labels for accessibility

**Testing**:
- [ ] Manual testing of all UI interactions
- [ ] Test error scenarios
- [ ] Test on different devices

**Labels**: `phase-4`, `frontend`, `ux`, `priority-medium`
""",
        "labels": ["phase-4", "frontend", "ux", "priority-medium"]
    },

    # Phase 5: Testing & Quality
    {
        "title": "Phase 5: Achieve 80% unit test coverage",
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: High
**Estimated Time**: 10 hours

**Description**:
Write unit tests for all core modules to achieve >80% coverage.

**Tasks**:
- [ ] Create unit tests for pipeline modules
- [ ] Create unit tests for agents
- [ ] Create unit tests for database modules
- [ ] Create unit tests for API utilities
- [ ] Mock external dependencies
- [ ] Test edge cases

**Acceptance Criteria**:
- [ ] >80% unit test coverage
- [ ] All edge cases tested
- [ ] All tests passing
- [ ] Coverage report generated

**Technical Details**:
Test files:
- `tests/unit/test_pdf_extractor.py`
- `tests/unit/test_chunker.py`
- `tests/unit/test_embeddings.py`
- `tests/unit/test_vector_store.py`
- `tests/unit/test_agents.py`

Use pytest and pytest-cov:
```bash
pytest --cov=src --cov-report=html tests/unit/
```

Mock external dependencies:
- Mock Ollama API calls
- Mock ChromaDB
- Mock FastAgent

**Testing**:
- [ ] Run coverage report
- [ ] Verify >80% coverage
- [ ] Review untested code

**Labels**: `phase-5`, `testing`, `priority-high`
""",
        "labels": ["phase-5", "testing", "priority-high"]
    },
    {
        "title": "Phase 5: Create integration test suite",
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: High
**Estimated Time**: 8 hours

**Description**:
Build integration tests for full pipeline and API endpoints.

**Tasks**:
- [ ] Create integration tests for pipeline (PDF → Vector DB)
- [ ] Create integration tests for API endpoints
- [ ] Create integration tests for agent coordination
- [ ] Test FastAgent + FastAPI integration
- [ ] Test error scenarios

**Acceptance Criteria**:
- [ ] Full pipeline tested end-to-end
- [ ] All API endpoints tested
- [ ] Agent coordination tested
- [ ] All tests passing

**Technical Details**:
Test files:
- `tests/integration/test_pipeline.py`
- `tests/integration/test_api.py`
- `tests/integration/test_agents.py`
- `tests/integration/test_fastagent_api.py`

Integration test setup:
- Use real Ollama (if available) or mock
- Use temporary ChromaDB instance
- Use test database files

**Testing**:
- [ ] Run integration test suite
- [ ] Verify all tests pass
- [ ] Check performance

**Labels**: `phase-5`, `testing`, `priority-high`
""",
        "labels": ["phase-5", "testing", "priority-high"]
    },
    {
        "title": "Phase 5: Build end-to-end tests",
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: Medium
**Estimated Time**: 6 hours

**Description**:
Create end-to-end tests for complete user flows.

**Tasks**:
- [ ] Create E2E test for document upload and processing
- [ ] Create E2E test for chat conversation
- [ ] Create E2E test for document viewing
- [ ] Test complete user journey
- [ ] Test error recovery

**Acceptance Criteria**:
- [ ] All user flows tested
- [ ] Error recovery tested
- [ ] All tests passing

**Technical Details**:
Test files:
- `tests/e2e/test_chat_flow.py`
- `tests/e2e/test_document_processing.py`
- `tests/e2e/test_user_journey.py`

E2E test setup:
- Start FastAPI server
- Start Gradio frontend
- Use httpx or playwright for testing
- Test complete workflows

**Testing**:
- [ ] Run E2E test suite
- [ ] Manual verification
- [ ] Performance check

**Labels**: `phase-5`, `testing`, `e2e`, `priority-medium`
""",
        "labels": ["phase-5", "testing", "e2e", "priority-medium"]
    },
    {
        "title": "Phase 5: Performance testing and optimization",
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: High
**Estimated Time**: 8 hours

**Description**:
Test performance with large documents and optimize bottlenecks.

**Tasks**:
- [ ] Test processing large PDFs (>100 pages)
- [ ] Measure query response times
- [ ] Test concurrent users
- [ ] Identify performance bottlenecks
- [ ] Optimize slow operations
- [ ] Create performance benchmarks

**Acceptance Criteria**:
- [ ] Large PDFs processed successfully
- [ ] Query response time <5s average
- [ ] Concurrent users supported
- [ ] Bottlenecks optimized
- [ ] Benchmarks documented

**Technical Details**:
Performance tests:
- PDF processing time vs file size
- Query response time distribution
- Concurrent request handling
- Memory usage profiling

Optimization targets:
- Batch embedding generation
- Vector search optimization
- Agent response caching
- Database query optimization

**Testing**:
- [ ] Run performance benchmarks
- [ ] Profile code with cProfile
- [ ] Optimize identified bottlenecks

**Labels**: `phase-5`, `testing`, `performance`, `priority-high`
""",
        "labels": ["phase-5", "testing", "performance", "priority-high"]
    },
    {
        "title": "Phase 5: Code review and refactoring",
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: Medium
**Estimated Time**: 8 hours

**Description**:
Review all code for quality, refactor as needed, and update documentation.

**Tasks**:
- [ ] Code review of all modules
- [ ] Refactor complex functions
- [ ] Remove duplicate code (DRY)
- [ ] Improve code readability
- [ ] Add missing docstrings and type hints
- [ ] Update inline documentation

**Acceptance Criteria**:
- [ ] All code reviewed
- [ ] Refactoring complete
- [ ] No duplicate code
- [ ] All functions documented
- [ ] Type hints complete

**Technical Details**:
Focus areas:
- Complex functions (>50 lines)
- Duplicate code patterns
- Missing error handling
- Unclear variable names
- Missing docstrings

Code quality checks:
- Run pylint/flake8
- Check type hints with mypy
- Verify docstring coverage
- Review test coverage gaps

**Testing**:
- [ ] Run all tests after refactoring
- [ ] Verify no regressions
- [ ] Update tests if needed

**Labels**: `phase-5`, `quality`, `refactoring`, `priority-medium`
""",
        "labels": ["phase-5", "quality", "refactoring", "priority-medium"]
    },

    # Phase 6: Documentation & Deployment
    {
        "title": "Phase 6: Write user documentation",
        "body": """**Phase**: 6 - Documentation & Deployment
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Create comprehensive user documentation for installation and usage.

**Tasks**:
- [ ] Write installation guide
- [ ] Create quick start tutorial
- [ ] Document configuration options
- [ ] Add troubleshooting guide
- [ ] Include screenshots and examples
- [ ] Create FAQ section

**Acceptance Criteria**:
- [ ] Installation guide complete
- [ ] Quick start tutorial working
- [ ] Configuration documented
- [ ] Troubleshooting guide helpful
- [ ] Examples included

**Technical Details**:
Documentation structure:
- `docs/installation.md` - Installation guide
- `docs/quickstart.md` - Quick start tutorial
- `docs/configuration.md` - Configuration reference
- `docs/troubleshooting.md` - Common issues
- `docs/faq.md` - Frequently asked questions

Include:
- System requirements
- Step-by-step installation
- Configuration examples
- Usage examples
- Common errors and solutions

**Testing**:
- [ ] Follow installation guide on fresh system
- [ ] Test quick start tutorial
- [ ] Verify all examples work

**Labels**: `phase-6`, `documentation`, `priority-high`
""",
        "labels": ["phase-6", "documentation", "priority-high"]
    },
    {
        "title": "Phase 6: Write developer documentation",
        "body": """**Phase**: 6 - Documentation & Deployment
**Priority**: Medium
**Estimated Time**: 8 hours

**Description**:
Create developer documentation for architecture, APIs, and contributing.

**Tasks**:
- [ ] Write architecture overview
- [ ] Document API reference
- [ ] Create agent development guide
- [ ] Write testing guide
- [ ] Add contributing guidelines
- [ ] Document code structure

**Acceptance Criteria**:
- [ ] Architecture documented
- [ ] API reference complete
- [ ] Development guides written
- [ ] Contributing guidelines clear
- [ ] Code structure explained

**Technical Details**:
Documentation structure:
- `docs/architecture.md` - System architecture
- `docs/api-reference.md` - API documentation
- `docs/agent-development.md` - Agent guide
- `docs/testing.md` - Testing guide
- `CONTRIBUTING.md` - Contributing guidelines

Include:
- Architecture diagrams
- API endpoint details
- Agent design patterns
- Testing best practices
- Code contribution workflow

**Testing**:
- [ ] Review by team members
- [ ] Verify examples work
- [ ] Check for clarity

**Labels**: `phase-6`, `documentation`, `priority-medium`
""",
        "labels": ["phase-6", "documentation", "priority-medium"]
    },
    {
        "title": "Phase 6: Create deployment guide",
        "body": """**Phase**: 6 - Documentation & Deployment
**Priority**: High
**Estimated Time**: 6 hours

**Description**:
Write deployment guide for local and production environments.

**Tasks**:
- [ ] Document local deployment steps
- [ ] Create Docker setup (optional)
- [ ] Document production considerations
- [ ] Add security best practices
- [ ] Include monitoring setup
- [ ] Document backup procedures

**Acceptance Criteria**:
- [ ] Local deployment documented
- [ ] Docker setup working (if included)
- [ ] Production guide complete
- [ ] Security documented
- [ ] Monitoring setup included

**Technical Details**:
Documentation structure:
- `docs/deployment.md` - Deployment guide
- `Dockerfile` - Docker configuration (optional)
- `docker-compose.yml` - Multi-container setup (optional)

Include:
- Environment setup
- Configuration management
- Process management (systemd, supervisor)
- Reverse proxy setup (nginx)
- SSL/TLS configuration
- Backup and restore

**Testing**:
- [ ] Test local deployment
- [ ] Test Docker setup (if included)
- [ ] Verify production recommendations

**Labels**: `phase-6`, `documentation`, `deployment`, `priority-high`
""",
        "labels": ["phase-6", "documentation", "deployment", "priority-high"]
    },
    {
        "title": "Phase 6: Final polish and bug fixes",
        "body": """**Phase**: 6 - Documentation & Deployment
**Priority**: High
**Estimated Time**: 10 hours

**Description**:
Final round of bug fixes, performance tuning, and UI improvements.

**Tasks**:
- [ ] Fix remaining bugs
- [ ] Performance tuning
- [ ] UI/UX improvements
- [ ] Final testing
- [ ] Update all documentation
- [ ] Prepare for release

**Acceptance Criteria**:
- [ ] All known bugs fixed
- [ ] Performance optimized
- [ ] UI polished
- [ ] All tests passing
- [ ] Documentation up to date
- [ ] Ready for release

**Technical Details**:
Focus areas:
- Critical bug fixes
- Performance bottlenecks
- UI/UX issues
- Documentation gaps
- Configuration issues

Final checks:
- Run full test suite
- Performance benchmarks
- Security audit
- Documentation review
- Release notes

**Testing**:
- [ ] Full regression testing
- [ ] User acceptance testing
- [ ] Performance verification
- [ ] Security check

**Labels**: `phase-6`, `bug-fix`, `polish`, `priority-high`
""",
        "labels": ["phase-6", "bug-fix", "polish", "priority-high"]
    }
]


def main():
    """Create all GitHub issues."""
    print("=" * 70)
    print("GitHub Issue Creator for Buddharauer Implementation Plan")
    print("=" * 70)
    print()

    # Get GitHub token
    token = get_github_token()
    print(f"✅ GitHub token found")
    print(f"📦 Repository: {GITHUB_OWNER}/{GITHUB_REPO}")
    print(f"📋 Creating {len(ISSUES)} issues...")
    print()

    # Create issues using shared utility function
    created_issues, failed_issues = batch_create_issues(token, ISSUES, verbose=True)

    # Print summary using shared utility function
    print_summary(created_issues, failed_issues)

    return 0 if not failed_issues else 1


if __name__ == "__main__":
    sys.exit(main())
