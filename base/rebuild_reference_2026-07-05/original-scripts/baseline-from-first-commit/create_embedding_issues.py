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

import os
import sys
import requests

# GitHub repository information
GITHUB_OWNER = "cdolan24"
GITHUB_REPO = "buddharauer"
GITHUB_API_URL = "https://api.github.com"

def get_github_token() -> str:
    """Get GitHub token from environment variable."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Γ¥î ERROR: GITHUB_TOKEN environment variable not set")
        print("\nTo create a GitHub token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token (classic)'")
        print("3. Select 'repo' scope")
        print("4. Copy the token and set: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)
    return token

def create_issue(token: str, title: str, body: str) -> dict:
    """Create a GitHub issue."""
    url = f"{GITHUB_API_URL}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": title,
        "body": body,
        "labels": ["phase-1", "priority", "embedding"]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# Define embedding generation issues
ISSUES = [
    {
        "title": "Implement Embedding Generation with Ollama",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Embedding Generation

**Description**:
Implement embedding generation module using Ollama's nomic-embed-text model for generating vector embeddings from text chunks.

**Status**: Complete Γ£à

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
    """Create GitHub issues."""
    token = get_github_token()
    
    for issue in ISSUES:
        print(f"Creating issue: {issue['title']}")
        response = create_issue(token, issue["title"], issue["body"])
        print(f"Created issue #{response['number']}")

if __name__ == "__main__":
    main()
