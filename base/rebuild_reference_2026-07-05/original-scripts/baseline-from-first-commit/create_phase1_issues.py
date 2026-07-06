#!/usr/bin/env python3
"""
Create GitHub Issues for Phase 1 Document Processing Pipeline

This script creates GitHub issues for Phase 1 priorities using the GitHub REST API.

Usage:
    python scripts/create_phase1_issues.py

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
        "labels": ["phase-1", "priority"]
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# Define Phase 1 priority issues
ISSUES = [
    {
        "title": "Implement PDF Text Extraction Module",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: PDF Text Extraction

**Description**:
Implement the PDF text extraction module using PyMuPDF to handle document processing.

**Tasks**:
- [ ] Create `src/pipeline/pdf_extractor.py`
- [ ] Implement text extraction with PyMuPDF
- [ ] Add metadata extraction (pages, title, etc.)
- [ ] Implement progress tracking for large PDFs
- [ ] Add error handling and logging
- [ ] Write unit tests

**Technical Details**:
- Use PyMuPDF for text extraction
- Handle different PDF formats
- Extract metadata including title, pages, chapters
- Implement progress tracking for large files

**Testing**:
- [ ] Test with various PDF types
- [ ] Verify metadata extraction
- [ ] Test progress tracking
- [ ] Test error handling
"""
    },
    {
        "title": "Implement Semantic Chunking Module",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Semantic Chunking

**Description**:
Create the semantic chunking module to intelligently split extracted text.

**Tasks**:
- [ ] Create `src/pipeline/chunker.py`
- [ ] Implement semantic chunking using LangChain
- [ ] Add configurable chunk size/overlap settings
- [ ] Implement metadata enrichment
- [ ] Handle special cases (tables, lists)
- [ ] Write unit tests

**Technical Details**:
- Use LangChain for semantic chunking
- Configurable chunk sizes and overlap
- Preserve document structure
- Handle edge cases properly

**Testing**:
- [ ] Test chunk size configurations
- [ ] Verify metadata preservation
- [ ] Test special case handling
- [ ] Validate chunk coherence
"""
    },
    {
        "title": "Implement Embedding Generation Module",
        "body": """**Phase**: 1 - Document Processing Pipeline
**Priority**: High
**Component**: Embedding Generation

**Description**:
Develop the embedding generation module using Ollama's nomic-embed-text model.

**Tasks**:
- [ ] Create `src/pipeline/embeddings.py`
- [ ] Integrate Ollama embeddings (nomic-embed-text)
- [ ] Implement batch processing
- [ ] Add progress tracking
- [ ] Implement error handling
- [ ] Write unit tests

**Technical Details**:
- Use nomic-embed-text model via Ollama
- Implement efficient batch processing
- Track progress for large documents
- Handle API errors gracefully

**Testing**:
- [ ] Test embedding generation
- [ ] Verify batch processing
- [ ] Test progress tracking
- [ ] Validate error handling
"""
    }
]

def main():
    """Create all Phase 1 priority issues."""
    token = get_github_token()
    
    print("Creating Phase 1 priority issues...")
    for issue in ISSUES:
        try:
            response = create_issue(token, issue["title"], issue["body"])
            print(f"Γ£à Created issue: {response['html_url']}")
        except Exception as e:
            print(f"Γ¥î Error creating issue '{issue['title']}': {str(e)}")
    
    print("\nDone! Check your GitHub repository for the new issues.")

if __name__ == "__main__":
    main()
