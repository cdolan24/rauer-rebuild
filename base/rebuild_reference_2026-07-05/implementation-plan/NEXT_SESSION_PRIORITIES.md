# Next Session Priorities

**Last Updated**: November 11, 2025 (Session 6)
**Current Status**: Phase 2 - FastAPI Backend (90% complete)

---

## Quick Status

- ✅ **Tests**: 115/115 passing (100%)
- ✅ **Coverage**: 91.62% (exceeds 90% target!)
- ✅ **Code Quality**: Excellent (clean, documented, no duplication)
- ✅ **Documentation**: Complete
- ✅ **Document Registry**: Implemented with 97% coverage

---

## Immediate Priorities (Next Session)

### 1. 🚀 Start Phase 3 - FastAgent Agents (Issue #23)
**Priority**: Critical Path | **Time**: 6-8 hours

This unblocks Phase 2 API completion!

**Tasks**:
1. Setup FastAgent with Ollama
   - Configure `fastagent.config.yaml`
   - Set environment variables (GENERIC_API_KEY, GENERIC_BASE_URL)
   - Test basic connectivity

2. Implement Retrieval Agent (RAG)
   - Create `src/agents/retrieval.py`
   - MCP tool for vector DB access
   - Use `generic.qwen2.5:latest`

3. Implement Orchestrator Agent
   - Create `src/agents/orchestrator.py`
   - Use `generic.llama3.2:latest`
   - Define tools for sub-agents

**Files to create**:
- `src/agents/__init__.py`
- `src/agents/retrieval.py`
- `src/agents/orchestrator.py`
- `fastagent.config.yaml` (if not exists)

### 2. 🔧 Complete Phase 2 - FastAPI Backend (Issue #22)
**Priority**: High | **Time**: 3-4 hours
**Status**: 90% complete (blocked on Phase 3 agents)

**Remaining Tasks**:
1. **Initialize services in API startup**
   - Uncomment VectorStore initialization in `src/api/main.py` (lines 86-88)
   - Uncomment DocumentRegistry initialization (lines 92-94)
   - Test lifespan startup/shutdown

2. **Implement document endpoints**
   - Update `src/api/routes/documents.py` to use DocumentRegistry
   - Replace placeholder implementations with real queries
   - Add document upload processing integration

3. **Implement search endpoints**
   - Update `src/api/routes/search.py` to use VectorStore
   - Add metadata filtering
   - Add similarity search

4. **Add dependency injection**
   - Update routes to use `Depends(get_vector_store)`
   - Update routes to use `Depends(get_document_registry)`
   - Test DI integration

**Files to modify**:
- [src/api/main.py](src/api/main.py) (lines 86-94, uncomment initialization)
- [src/api/routes/documents.py](src/api/routes/documents.py) (replace placeholders)
- [src/api/routes/search.py](src/api/routes/search.py) (integrate VectorStore)

### 3. 📊 Optional: Improve API Test Coverage
**Priority**: Medium | **Time**: 2-3 hours

Currently API routes have lower coverage (56-71%) because they're placeholder implementations.
After integrating services, add tests for:
- Document upload and processing
- Search with real VectorStore
- Error handling in API routes

---

## Context from Session 6

### What Was Accomplished ✅

1. **Test Coverage Achievement**:
   - Increased from 88.04% to **91.62%**
   - Added 11 new tests (104 → 115 tests)
   - All tests passing (100% pass rate)
   - Closed issue #24

2. **Module-Specific Improvements**:
   - `embeddings.py`: 79% → 99% (+4 tests)
   - `vector_store.py`: 89% → 99% (+4 tests)
   - `document_registry.py`: 97% (new, +11 tests)

3. **Document Registry Implementation**:
   - Created complete SQLite-based registry (543 lines)
   - Async/await interface with aiosqlite
   - Full CRUD operations
   - Document lifecycle tracking
   - Processing statistics
   - Comprehensive test suite

4. **Code Quality Review**:
   - Reviewed all core modules
   - Confirmed clean, well-documented code
   - No redundant or duplicate code found
   - All modules have comprehensive docstrings

5. **Dependencies**:
   - Added `aiosqlite>=0.19.0` to requirements.txt

### Key Files Modified
- ✅ `tests/unit/test_embeddings_enhanced.py` (+4 tests)
- ✅ `tests/unit/test_vector_store.py` (+4 tests)
- ✅ `src/database/document_registry.py` (new, 543 lines)
- ✅ `tests/unit/test_document_registry.py` (new, 278 lines)
- ✅ `requirements.txt` (added aiosqlite)

### Git Commits
- `1ded8b8` - feat: Improve test coverage to 91.62% and add document registry

---

## Important Notes

### Architecture Context
- **Hybrid Approach**: FastAgent (agents) + FastAPI (REST) + Ollama (local models)
- **Current Phase**: Phase 2 (90% complete) - blocked on Phase 3
- **Critical Path**: Phase 3 agents → Phase 2 API completion → Phase 4 UI

### FastAgent Setup Requirements
- **Python Version**: 3.13.5+ (required for FastAgent)
- **Ollama Models**:
  - llama3.2:latest (orchestrator, analyst)
  - qwen2.5:latest (alternative, better tool calling)
  - mistral:7b (web search)
  - nomic-embed-text (embeddings)
- **Tool Calling**: Officially tested with llama3.2 and qwen2.5
- **Config Location**: `fastagent.config.yaml` in project root

### Known Issues
- Document registry uses `datetime.utcnow()` which is deprecated in Python 3.12+
  - Should use `datetime.now(datetime.UTC)` instead
  - Not critical but should be fixed in a cleanup pass

### Testing Strategy
- Focus on integration tests after services are wired up
- Don't test API stubs (implement functionality first)
- Target: 90%+ overall, >85% per module
- All new tests must be reliable (no flaky tests)

### GitHub Issues

#### Open Issues (Priority Order)
1. **#23** - Phase 3: Implement FastAgent Agents with Ollama (HIGH PRIORITY)
2. **#22** - Phase 2: Complete FastAPI Backend Integration (HIGH PRIORITY)
3. **#7** - CI/CD: Configure GitHub Actions Workflow
4. **#10** - Prepare ChromaDB Migration
5. **#11** - Performance Optimization Phase

#### Recently Closed
- **#24** - Improve test coverage from 88% to 90%+ ✅ (Session 6)
- **#25** - Code quality and documentation improvements ✅ (Session 4)

---

## Quick Commands

### Run Tests
```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html

# Specific module
python -m pytest tests/unit/test_document_registry.py -v
```

### FastAgent Setup
```bash
# Initialize FastAgent
fast-agent setup

# Test with Ollama
fast-agent --model generic.llama3.2:latest

# Check Ollama status
ollama list
curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test"}'
```

### Git Commands
```bash
# Status
git status

# Create feature branch
git checkout -b feature/phase3-agents

# GitHub issues
gh issue list
gh issue view 23
```

---

## Questions to Consider

1. **Ollama Setup**: Is Ollama running? Are all models pulled?
2. **FastAgent Config**: Does `fastagent.config.yaml` exist with correct settings?
3. **Testing Approach**: Should we test agents independently or integration-first?
4. **API Integration**: Should we complete API first or agents first?
   - **Recommendation**: Agents first (Phase 3), then wire to API

---

## Resources

- [CLAUDE.md](CLAUDE.md) - Project overview and architecture
- [ARCHITECTURE_V2.md](specs/ARCHITECTURE_V2.md) - V2 architecture details
- [IMPLEMENTATION_PLAN.md](specs/IMPLEMENTATION_PLAN.md) - Full implementation plan
- [FastAgent Docs](https://github.com/anthropics/fast-agent-mcp) - Framework documentation
- [Ollama Docs](https://github.com/ollama/ollama) - Local LLM server

---

## Session Handoff Checklist

For the next session, ensure you:
- [ ] Check Ollama is running (`ollama list`)
- [ ] Pull required models if missing
- [ ] Create `fastagent.config.yaml`
- [ ] Test FastAgent + Ollama connectivity
- [ ] Start with Retrieval Agent implementation
- [ ] Then implement Orchestrator Agent
- [ ] Finally wire agents to API endpoints

---

*This file provides quick context for starting the next session*
*Updated after Session 6: November 11, 2025*
