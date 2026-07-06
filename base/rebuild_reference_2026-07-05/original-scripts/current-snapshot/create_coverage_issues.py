#!/usr/bin/env python3
"""
Create GitHub Issues for Test Coverage Improvements

This script creates GitHub issues to track test coverage improvement tasks.

Usage:
    python scripts/create_coverage_issues.py

Requirements:
    - requests library: pip install requests
    - GitHub Personal Access Token with repo scope
    - Set GITHUB_TOKEN environment variable
"""

import sys
from github_utils import get_github_token, batch_create_issues, print_summary

# Define test coverage improvement issues
ISSUES = [
    {
        "title": "Improve test coverage from 88% to 90%+",
        "labels": ["testing", "priority-high", "phase-5"],
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: High
**Component**: Test Coverage

**Description**:
Increase overall test coverage from current 88% to target of 90%+.

**Current Coverage Status**:
- Overall: 88.04%
- API routes: 56-71% (many stubs/TODOs)
- Pipeline modules: 79-98% (good)
- Database modules: 89-95% (good)
- Utils: 100% (excellent)

**Tasks**:
- [ ] Add tests for embeddings error paths (currently 79%)
- [ ] Add tests for API main.py lifecycle methods (currently 56%)
- [ ] Add tests for vector_store error cases (currently 89%)
- [ ] Add tests for pdf_extractor edge cases (currently 89%)
- [ ] Improve orchestrator test coverage (currently 94%)

**Modules Needing Improvement**:

### High Priority (Below 80%)
- **embeddings.py**: 79% coverage
  - Missing: Lines 103-106, 150, 180-183, 187->170, 200-204
  - Needs: Error path tests, edge case tests

### Medium Priority (80-90%)
- **vector_store.py**: 89% coverage
  - Missing: Lines 70-76, 152, 357, 417-419
  - Needs: Error condition tests

- **pdf_extractor.py**: 89% coverage
  - Missing: Lines 85, 92, 96, 158, 188, 241->246, 263-268
  - Needs: Edge case tests, error handling tests

### API Routes (Mostly TODOs - Low Priority)
These are placeholder implementations and should be tested when implemented:
- api/main.py: 56%
- api/routes/documents.py: 61%
- api/routes/health.py: 63%
- api/routes/search.py: 71%

**Acceptance Criteria**:
- [ ] Overall coverage >90%
- [ ] All pipeline modules >85%
- [ ] All database modules >90%
- [ ] All utils >95%
- [ ] Integration tests for API routes when implemented

**Technical Details**:
Run coverage report:
```bash
pytest --cov=src --cov-report=html tests/
```

View report:
```bash
# Open htmlcov/index.html in browser
```

**Testing**:
- [ ] Verify coverage increased to 90%+
- [ ] Ensure all new tests pass
- [ ] Check for flaky tests
- [ ] Document any uncoverable code

**Related Issues**:
- Depends on API implementation (#11-#15)
- Blocks production readiness
"""
    },
    {
        "title": "Add tests for embeddings error handling and edge cases",
        "labels": ["testing", "priority-high", "embeddings"],
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: High
**Component**: Embeddings Testing

**Description**:
Add comprehensive tests for embeddings module error handling and edge cases to increase coverage from 79% to 90%+.

**Current Coverage**: 79% (14 lines missing, 4 branches missing)

**Missing Coverage**:
- Lines 103-106: HTTPError retry path
- Line 150: Empty texts list edge case
- Lines 180-183: Batch error handling
- Lines 187->170: Loop branch
- Lines 200-204: Error logging

**Tasks**:
- [ ] Test HTTP error retry logic (lines 103-106)
- [ ] Test empty texts list (line 150)
- [ ] Test batch processing errors (lines 180-183)
- [ ] Test error logging output (lines 200-204)
- [ ] Test slow embedding warnings (line 111)
- [ ] Test concurrent batch processing
- [ ] Test cache miss/hit scenarios

**Test Cases to Add**:
```python
# Test HTTP errors with retries
async def test_http_error_retries():
    # Mock API to fail then succeed
    pass

# Test empty input
async def test_empty_texts_list():
    result = await generator.batch_generate_embeddings([])
    assert result == {}

# Test batch errors
async def test_batch_with_some_errors():
    # Test ignore_errors=True
    pass

# Test error logging
async def test_error_logging_output(caplog):
    # Verify error messages logged correctly
    pass
```

**Acceptance Criteria**:
- [ ] Embeddings coverage >90%
- [ ] All error paths tested
- [ ] All edge cases covered
- [ ] All tests pass reliably

**Related**:
- Parent issue: #18 (Improve test coverage to 90%+)
"""
    },
    {
        "title": "Code cleanup and documentation improvements",
        "labels": ["documentation", "code-quality", "priority-medium"],
        "body": """**Phase**: 5 - Testing & Quality
**Priority**: Medium
**Component**: Code Quality

**Description**:
Clean up codebase and improve documentation consistency.

**Completed**:
- ✅ Consolidated GitHub API helper functions into shared `scripts/github_utils.py`
- ✅ Refactored 3 issue creation scripts to eliminate ~150 lines of duplication
- ✅ Added comprehensive docstrings to shared utilities
- ✅ All pipeline code well-documented with Google-style docstrings

**Tasks**:
- [ ] Remove any remaining redundant/duplicate code
- [ ] Add comments to complex algorithms
- [ ] Standardize naming conventions
- [ ] Clean up commented-out code
- [ ] Update docstrings to be consistent (all Google style)
- [ ] Add type hints to remaining functions missing them
- [ ] Ensure all public methods have docstrings

**Code Quality Checks**:
- [ ] Run pylint/flake8
- [ ] Check type hints with mypy
- [ ] Verify docstring coverage
- [ ] Review test coverage gaps

**Files Needing Attention**:
- ✅ `scripts/create_github_issues.py` - Refactored
- ✅ `scripts/create_embedding_issues.py` - Refactored
- ✅ `scripts/create_phase1_issues.py` - Refactored
- ✅ `scripts/github_utils.py` - Created (new shared module)
- All API routes - Add docstrings when implementing TODOs

**Benefits**:
- Easier onboarding for new developers
- Reduced maintenance burden
- Better IDE autocomplete support
- Clearer error debugging
- Eliminated ~150 lines of duplicate code

**Acceptance Criteria**:
- [ ] No duplicate code patterns
- [ ] All public functions have docstrings
- [ ] Type hints complete
- [ ] Code passes linting
- [ ] Documentation is consistent

**Related**:
- Part of Phase 5 quality improvements
"""
    }
]

def main():
    """Create GitHub issues for test coverage improvements."""
    print("Creating test coverage improvement issues...")
    print()

    # Get GitHub token
    token = get_github_token()

    # Create issues using shared utility function
    created_issues, failed_issues = batch_create_issues(token, ISSUES, verbose=True)

    # Print summary using shared utility function
    print_summary(created_issues, failed_issues)

    return 0 if not failed_issues else 1

if __name__ == "__main__":
    sys.exit(main())
