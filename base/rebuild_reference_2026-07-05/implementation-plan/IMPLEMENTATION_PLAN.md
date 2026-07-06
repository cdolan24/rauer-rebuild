# Implementation Plan - Buddharauer V2

## Overview

This document outlines the prioritized implementation plan for Buddharauer V2, a local-first RAG application with Ollama, FastAPI, and Gradio.

**Architecture**: Local models (Ollama) + FastAPI backend + Gradio frontend
**Timeline**: 6 weeks MVP
**Approach**: Iterative development with continuous testing

---

## Development Phases

### Phase 0: Environment Setup (Week 1)

**Goal**: Set up development environment and verify all components work

**Tasks**:
1. ✅ **Install Ollama**
   - Download from https://ollama.ai/
   - Pull models for FastAgent:
     - `ollama pull llama3.2:latest` (orchestrator, analyst)
     - `ollama pull qwen2.5:latest` (alternative, better tool calling)
     - `ollama pull mistral:7b` (web search)
     - `ollama pull nomic-embed-text` (embeddings)
   - Verify: `ollama list`

2. ✅ **Create Project Structure**
   ```bash
   mkdir -p src/{api,agents,pipeline,database,frontend,utils}
   mkdir -p tests/{unit,integration,e2e}
   mkdir -p data processed vector_db data_storage scripts
   ```

3. ✅ **Setup Python Environment**
   - Python 3.13.5+ (required for FastAgent)
   - Create `requirements.txt`
   - Create `config.example.yaml`
   - Setup git + .gitignore

4. ✅ **Install Core Dependencies**
   ```bash
   # Install with uv (recommended) or pip
   uv pip install fast-agent-mcp>=0.3.17
   uv pip install fastapi uvicorn gradio chromadb
   uv pip install pymupdf pillow python-dotenv pyyaml
   uv pip install pytest pytest-asyncio pytest-cov httpx
   ```

5. ✅ **Create Config System**
   - `src/utils/config.py` - YAML config loader
   - `config.example.yaml` - Application config template
   - `fastagent.config.yaml` - FastAgent LLM provider config
   - Environment variable support

6. ✅ **Verify Ollama + FastAgent Integration**
   - Test Ollama API: `curl http://localhost:11434/api/generate`
   - Test FastAgent setup: `fast-agent setup`
   - Verify model responses: `fast-agent --model generic.llama3.2:latest`
   - Test embeddings generation via Ollama API
   - Confirm tool calling works with Ollama models

**Deliverables**:
- ✅ Working dev environment
- ✅ All tools installed and verified
- ✅ Basic project structure
- ✅ Configuration system

**GitHub Issues**:
- #1: Setup Ollama and pull models (llama3.2, qwen2.5, mistral, nomic-embed-text)
- #2: Create project structure and dependencies (FastAgent, FastAPI, Gradio)
- #3: Implement configuration system (config.yaml + fastagent.config.yaml)
- #4: Verify Ollama + FastAgent integration with generic provider

---

### Phase 1: Document Processing Pipeline (Week 2)

**Goal**: Process PDFs into vector database

**Tasks**:
1. **PDF Text Extraction**
   - `src/pipeline/pdf_extractor.py`
   - Extract text with PyMuPDF
   - Extract metadata (pages, title, etc.)
   - Handle large PDFs (progress tracking)

2. **Semantic Chunking**
   - `src/pipeline/chunker.py`
   - Implement semantic chunking (LangChain)
   - Configurable chunk size/overlap
   - Metadata enrichment (page, chapter, etc.)
   - Handle edge cases (tables, lists)

3. **Embedding Generation**
   - `src/pipeline/embeddings.py`
   - Use Ollama embeddings (`nomic-embed-text`)
   - Batch processing for efficiency
   - Progress tracking for large documents

4. **Vector Database Setup**
   - `src/database/vector_store.py`
   - ChromaDB initialization
   - Upsert chunks with metadata
   - Search interface

5. **Document Registry**
   - `src/database/document_registry.py`
   - SQLite database for tracking
   - Track processing status
   - Link to vector DB

6. **Processing Script**
   - `scripts/process_documents.py`
   - CLI for processing PDFs
   - Batch and single-file modes
   - Progress bars

**Deliverables**:
- Working PDF → Vector DB pipeline
- Processed test documents
- Document registry database

**Tests**:
- `tests/unit/test_chunking.py`
- `tests/unit/test_embeddings.py`
- `tests/integration/test_pipeline.py`

**GitHub Issues**:
- #5: Implement PDF text extraction
- #6: Create semantic chunking system
- #7: Setup Ollama embeddings generation
- #8: Integrate ChromaDB vector store
- #9: Create document registry
- #10: Build processing script with CLI

---

### Phase 2: FastAPI Backend (Week 2-3)

**Goal**: Create REST API for frontend

**Tasks**:
1. **API Foundation**
   - `src/api/main.py` - FastAPI app
   - CORS configuration for Gradio
   - Error handling middleware
   - Request/response models (Pydantic)

2. **Core Endpoints**
   - `src/api/routes/chat.py`:
     - `POST /api/chat` - Chat endpoint
     - `GET /api/conversations/{id}` - Get history
     - `DELETE /api/conversations/{id}` - Clear chat

   - `src/api/routes/documents.py`:
     - `GET /api/documents` - List documents
     - `GET /api/documents/{id}` - Get document
     - `GET /api/documents/{id}/content` - Get content
     - `POST /api/documents/upload` - Upload PDF

   - `src/api/routes/search.py`:
     - `POST /api/search` - Vector search

   - `src/api/routes/health.py`:
     - `GET /api/health` - System status

3. **Query Logger**
   - `src/database/query_logger.py`
   - Log all queries to SQLite
   - Track response times
   - User tracking (optional)

4. **API Models**
   - `src/api/models/` - Pydantic models
   - Request/response schemas
   - Validation

**Deliverables**:
- Working FastAPI server
- All core endpoints implemented
- API documentation (Swagger)

**Tests**:
- `tests/integration/test_api.py`
- `tests/integration/test_endpoints.py`

**GitHub Issues**:
- #11: Setup FastAPI application structure
- #12: Implement chat endpoint
- #13: Implement document endpoints
- #14: Create query logger
- #15: Add API tests

---

### Phase 3: FastAgent Agents Implementation (Week 3-4)

**Goal**: Build FastAgent agents with Ollama local models

**Tasks**:
1. **FastAgent Setup & Configuration**
   - Install `fast-agent-mcp` (v0.3.17+, requires Python 3.13.5+)
   - Create `fastagent.config.yaml` with Ollama generic provider
   - Set up environment variables (GENERIC_API_KEY, GENERIC_BASE_URL)
   - Test basic FastAgent + Ollama connectivity
   - Create `src/utils/fastagent_client.py` wrapper

2. **Retrieval Agent (RAG) - FastAgent**
   - `src/agents/retrieval.py`
   - Define as FastAgent tool or sub-agent
   - Create MCP tool for vector DB access
   - Use `generic.qwen2.5:latest` for query reformulation
   - Integrate with ChromaDB for semantic search
   - Return chunks with citations

3. **Orchestrator Agent - FastAgent**
   - `src/agents/orchestrator.py`
   - Main FastAgent agent with model `generic.llama3.2:latest`
   - Define tools for sub-agents (analyst, retrieval, web_search)
   - Manage conversation context via FastAgent memory
   - Route to appropriate sub-agent based on intent
   - Format responses with source citations

4. **Analyst Agent - FastAgent**
   - `src/agents/analyst.py`
   - FastAgent sub-agent for summarization and analysis
   - Model: `generic.llama3.2:latest` or `generic.qwen2.5:latest`
   - Summarize content, extract entities, provide creative insights
   - Generate explanatory responses (for Faraday user profile)

5. **Web Search Agent - FastAgent**
   - `src/agents/web_search.py`
   - FastAgent sub-agent with MCP web search tools
   - Model: `generic.mistral:7b` (fast summarization)
   - Integrate with DuckDuckGo MCP server (or similar)
   - Query formulation and result summarization

6. **FastAPI Integration Layer**
   - `src/api/routes/chat.py` - Call FastAgent orchestrator from FastAPI endpoint
   - Initialize orchestrator on app startup
   - Handle async calls to agents
   - Extract sources and format responses
   - Error handling for agent failures

**Deliverables**:
- All 4 FastAgent agents implemented with Ollama
- FastAgent + FastAPI integration working
- Conversation memory via FastAgent
- MCP tools for vector DB and web search

**Tests**:
- `tests/unit/test_fastagent_config.py` - Test Ollama configuration
- `tests/unit/test_agents.py` - Test individual agents
- `tests/integration/test_fastagent_api.py` - Test FastAPI + FastAgent integration
- `tests/integration/test_agent_coordination.py` - Test orchestrator routing

**GitHub Issues**:
- #16: Setup FastAgent with Ollama generic provider
- #17: Implement RAG retrieval agent (FastAgent)
- #18: Implement orchestrator agent (FastAgent)
- #19: Implement analyst agent (FastAgent)
- #20: Implement web search agent (FastAgent)
- #21: Integrate FastAgent with FastAPI endpoints

---

### Phase 4: Gradio Frontend (Week 4-5)

**Goal**: Build chat interface with document viewer

**Tasks**:
1. **Gradio App Setup**
   - `src/frontend/app.py`
   - Basic layout (chat + document viewer)
   - Theme configuration

2. **Chat Component**
   - `src/frontend/components/chat.py`
   - Chat interface with history
   - Message formatting
   - Source citations display

3. **Document Viewer Component**
   - `src/frontend/components/document_viewer.py`
   - Markdown/text display
   - Highlight citations
   - Scroll to relevant sections

4. **Document Management UI**
   - Document selector dropdown
   - Upload interface
   - Processing status display

5. **Backend Integration**
   - API client (`src/frontend/api_client.py`)
   - WebSocket for real-time updates (optional)
   - Error handling and user feedback

6. **UI Polish**
   - Loading states
   - Error messages
   - Responsive design
   - Theme customization

**Deliverables**:
- Working Gradio interface
- Chat + document viewer
- Full API integration

**Tests**:
- `tests/e2e/test_chat_flow.py`
- Manual UI testing

**GitHub Issues**:
- #22: Setup Gradio application
- #23: Create chat component
- #24: Create document viewer component
- #25: Implement document management UI
- #26: Integrate with FastAPI backend
- #27: Polish UI and add error handling

---

### Phase 5: Testing & Quality (Week 5)

**Goal**: Comprehensive testing and quality assurance

**Tasks**:
1. **Unit Test Coverage**
   - All core modules >80% coverage
   - Edge case testing
   - Mock external dependencies

2. **Integration Tests**
   - Full pipeline tests
   - API endpoint tests
   - Agent interaction tests

3. **End-to-End Tests**
   - Complete user flows
   - Chat conversations
   - Document processing

4. **Performance Testing**
   - Large PDF processing
   - Query response times
   - Concurrent users

5. **Quality Improvements**
   - Code review
   - Refactoring
   - Documentation

**Deliverables**:
- >80% test coverage
- Performance benchmarks
- Bug fixes

**Tests**:
- Complete test suite in `tests/`

**GitHub Issues**:
- #28: Achieve 80% unit test coverage
- #29: Create integration test suite
- #30: Build end-to-end tests
- #31: Performance testing and optimization
- #32: Code review and refactoring

---

### Phase 6: Documentation & Deployment (Week 6)

**Goal**: Complete documentation and deployment guide

**Tasks**:
1. **User Documentation**
   - Installation guide
   - Quick start tutorial
   - Configuration reference
   - Troubleshooting

2. **Developer Documentation**
   - Architecture overview
   - API reference
   - Agent development guide
   - Testing guide

3. **Deployment Guide**
   - Local deployment
   - Docker setup (optional)
   - Production considerations

4. **Final Polish**
   - Bug fixes
   - Performance tuning
   - UI improvements

**Deliverables**:
- Complete documentation
- Deployment guide
- Docker support (optional)

**GitHub Issues**:
- #33: Write user documentation
- #34: Write developer documentation
- #35: Create deployment guide
- #36: Final polish and bug fixes

---

## GitHub Issues Template

For each task, create issues with:

```markdown
### Issue Title: [Task Name]

**Phase**: [Phase Number]
**Priority**: High/Medium/Low
**Estimated Time**: [Hours/Days]

**Description**:
[Detailed description of the task]

**Acceptance Criteria**:
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Tests written and passing

**Technical Details**:
- Files to create/modify
- Dependencies needed
- Related issues

**Testing**:
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

**Labels**: `phase-X`, `backend/frontend/agent`, `priority-high/medium/low`
```

---

## Priority Matrix

### Must Have (MVP)
- ✅ PDF processing pipeline
- ✅ Vector database integration
- ✅ Orchestrator & Retrieval agents
- ✅ FastAPI backend
- ✅ Basic Gradio UI (chat + viewer)
- ✅ Core testing

### Should Have
- ✅ Analyst agent
- ✅ Web search agent
- ✅ Query logging
- ✅ Document management UI
- ✅ Comprehensive tests

### Nice to Have
- ⏸️ Image extraction
- ⏸️ Advanced analytics
- ⏸️ User authentication
- ⏸️ Docker deployment
- ⏸️ Multiple frontend options

### Future
- ⏸️ Multi-user support
- ⏸️ Cloud deployment
- ⏸️ Advanced visualization
- ⏸️ Mobile app

---

## Weekly Handoff Checklist

At the end of each week/session, update:

### 1. Progress Tracking
- [ ] Update GitHub issues with progress
- [ ] Close completed issues
- [ ] Create new issues if needed
- [ ] Update project board

### 2. Documentation Updates
- [ ] Update IMPLEMENTATION_PLAN.md with progress
- [ ] Update README.md if architecture changed
- [ ] Update CLAUDE.md for next session
- [ ] Document any blockers or decisions

### 3. Code Quality
- [ ] Run tests and ensure passing
- [ ] Update test coverage report
- [ ] Code review if working with others
- [ ] Update dependencies if changed

### 4. Next Session Prep
- [ ] Prioritize next phase tasks
- [ ] Note any environment changes needed
- [ ] List questions or decisions needed
- [ ] Update specs if requirements changed

---

## Code Quality Standards

**IMPORTANT**: All code must be written with the following standards:

### Documentation Requirements
- **Docstrings**: All functions, classes, and modules must have clear docstrings
  - Use Google-style or NumPy-style docstrings
  - Include parameter types, return types, and exceptions
  - Provide usage examples for complex functions

- **Comments**:
  - Explain WHY, not WHAT (code should be self-explanatory)
  - Comment complex algorithms, business logic, and workarounds
  - Use TODO/FIXME/NOTE tags appropriately

- **Type Hints**: Use Python type hints throughout
  - All function parameters and return types
  - Complex data structures with TypedDict or dataclasses

### Code Readability
- **Naming**: Use clear, descriptive names
  - Functions: `verb_noun` (e.g., `process_document`, `extract_entities`)
  - Classes: `PascalCase` (e.g., `DocumentProcessor`, `VectorStore`)
  - Constants: `UPPER_SNAKE_CASE`

- **Structure**:
  - Keep functions short (ideally <50 lines)
  - Single Responsibility Principle
  - DRY (Don't Repeat Yourself)

- **Error Handling**:
  - Explicit exception handling with meaningful messages
  - Log errors with context
  - Fail gracefully with user-friendly messages

### Example Code Style
```python
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class DocumentChunk:
    """Represents a chunk of text from a processed document.

    Attributes:
        chunk_id: Unique identifier for this chunk
        document_id: ID of parent document
        text: The actual text content
        page_start: Starting page number
        metadata: Additional metadata (chapter, section, etc.)
    """
    chunk_id: str
    document_id: str
    text: str
    page_start: int
    metadata: Dict[str, any]

def process_pdf_document(
    file_path: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150
) -> List[DocumentChunk]:
    """Extract and chunk text from a PDF document.

    Args:
        file_path: Path to the PDF file
        chunk_size: Target size for text chunks in tokens
        chunk_overlap: Number of overlapping tokens between chunks

    Returns:
        List of DocumentChunk objects containing processed text

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        PDFProcessingError: If PDF cannot be processed

    Example:
        >>> chunks = process_pdf_document("data/sample.pdf")
        >>> print(f"Created {len(chunks)} chunks")
    """
    # Implementation with clear logic flow and comments
    pass
```

---

## Risk Management

| Risk | Mitigation |
|------|------------|
| **Ollama performance** | Test with different models, adjust hardware recommendations |
| **Large PDF processing** | Implement batching, progress tracking, timeout handling |
| **Vector DB scaling** | Use Qdrant for production, optimize chunking |
| **Agent quality** | Extensive prompt engineering, user feedback loop |
| **API latency** | Async processing, caching, streaming responses |
| **Code maintainability** | Enforce code quality standards, regular code reviews, comprehensive docs |

---

## Success Metrics

### MVP Success (End of Week 6)
- ✅ Process 10+ PDFs successfully
- ✅ Chat interface functional
- ✅ <5s query response time (average)
- ✅ >80% test coverage
- ✅ Documentation complete

### Production Ready (Future)
- ⏸️ Process 100+ PDFs
- ⏸️ <2s query response time
- ⏸️ >90% test coverage
- ⏸️ Docker deployment
- ⏸️ Multi-user support

---

## Next Steps

1. **Immediate**: Start Phase 0 - Environment setup
2. **Week 1**: Complete setup, start Phase 1
3. **Week 2-3**: Backend + Pipeline
4. **Week 4-5**: Agents + Frontend
5. **Week 6**: Testing + Documentation

---

*Last updated: 2025-11-05*
*Current Phase: 0 (Planning Complete)*
*Next: Environment Setup*
