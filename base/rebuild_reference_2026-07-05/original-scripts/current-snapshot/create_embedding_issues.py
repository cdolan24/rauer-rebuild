"""
Create GitHub Issues for Embedding Generation

This script creates GitHub issues for embedding generation using the GitHub REST API.

Usage:
    python scripts/create_embedding_issues.py

Requirements:
    - requests library: pip install requests
    - GitHub Personal Access Token with repo scope
    - Set GITHUB_TOKEN environment variable
"""

from github_utils import get_github_token, batch_create_issues, print_summary

# Define embedding generation issues with default labels
ISSUES = [
    {
        "title": "Implement Embedding Generation with Ollama",
        "labels": ["phase-1", "priority", "embedding"],
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Embedding Generation

**Description**:
Implement embedding generation module using Ollama's nomic-embed-text model for generating vector embeddings from text chunks.

**Status**: Complete ✅

**Tasks**:
- [x] Create `src/pipeline/embeddings.py`
- [x] Implement EmbeddingGenerator class
- [x] Add caching support for embeddings
- [x] Add batch processing (100 chunks per batch)
- [x] Write comprehensive tests
- [x] Configure nomic-embed-text model
- [x] Add async/await support for better performance

**Technical Details**:
- Using Ollama's nomic-embed-text model
- HTTP API integration with async support (httpx)
- JSON-based caching with SHA256 hashing
- Batched processing for efficiency
- Full test coverage with pytest-asyncio

**Testing**:
- [x] Test embedding generation
- [x] Test caching functionality
- [x] Test batch processing
- [x] Test error handling

**Next Steps**:
1. Integrate with ChromaDB vector store
2. Add metadata support
3. Add search functionality
4. Add monitoring and logging
5. Add retries and timeout configuration

**Files**:
- `src/pipeline/embeddings.py`: Main implementation
- `tests/unit/test_embeddings.py`: Test suite
"""
    },
    {
        "title": "Integrate Embeddings with Vector Store",
        "labels": ["phase-1", "priority", "embedding"],
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Vector Storage

**Description**:
Integrate the embedding generation module with ChromaDB for efficient vector storage and retrieval.

**Tasks**:
- [ ] Create `src/database/vector_store.py`
- [ ] Set up ChromaDB integration
- [ ] Implement document storage with metadata
- [ ] Add search functionality with configurable k
- [ ] Add bulk upsert support
- [ ] Write unit tests

**Technical Details**:
- Use ChromaDB for vector storage
- Store document metadata with embeddings
- Support similarity search
- Handle batch operations efficiently

**Testing**:
- [ ] Test document storage
- [ ] Test similarity search
- [ ] Test metadata handling
- [ ] Test bulk operations
- [ ] Test concurrent access

**Dependencies**:
- Embedding generation module
- ChromaDB setup
"""
    },
    {
        "title": "Add Embedding System Improvements",
        "labels": ["phase-1", "priority", "embedding"],
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: Medium
**Component**: Embedding System

**Description**:
Enhance the embedding system with additional features and robustness improvements.

**Tasks**:
- [ ] Add retry logic for API failures
- [ ] Add comprehensive logging
- [ ] Add dimension validation
- [ ] Add type hints for dimensions
- [ ] Make batch size configurable
- [ ] Add timeout configuration
- [ ] Add progress tracking
- [ ] Write additional tests

**Technical Details**:
- Implement exponential backoff for retries
- Add structured logging
- Validate embedding dimensions
- Add configuration system
- Track embedding progress

**Testing**:
- [ ] Test retry logic
- [ ] Test logging output
- [ ] Test dimension validation
- [ ] Test configuration system
- [ ] Test progress tracking
"""
    }
]

def main():
    """Create GitHub issues for embedding generation."""
    print("Creating embedding generation issues...")
    print()

    # Get GitHub token
    token = get_github_token()

    # Create issues using shared utility function
    created_issues, failed_issues = batch_create_issues(token, ISSUES, verbose=True)

    # Print summary using shared utility function
    print_summary(created_issues, failed_issues)

    return 0 if not failed_issues else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())