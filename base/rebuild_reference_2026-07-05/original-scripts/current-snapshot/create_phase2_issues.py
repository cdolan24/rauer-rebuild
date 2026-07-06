"""Script to create GitHub issues for the next phase of development."""
import os
import requests
from typing import List, Dict, Any

# Configuration
REPO_OWNER = "cdolan24"
REPO_NAME = "buddharauer"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Set this in your environment

ISSUES = [
    {
        "title": "CI/CD: Configure GitHub Actions Workflow",
        "body": """# CI/CD Pipeline Setup

## Objective
Set up comprehensive CI/CD pipeline using GitHub Actions.

## Tasks
- [ ] Create GitHub Actions workflow file
- [ ] Configure test automation
- [ ] Set up coverage reporting with codecov
- [ ] Add linting with black and flake8
- [ ] Add type checking with mypy
- [ ] Create deployment pipeline

## Acceptance Criteria
- GitHub Actions workflow passing
- Tests running automatically on PRs
- Coverage reports generated
- Code quality checks implemented
- Documentation for CI/CD process

## Dependencies
None

## Priority
High

## Labels
- ci-cd
- infrastructure
- high-priority""",
        "labels": ["ci-cd", "infrastructure", "high-priority"]
    },
    {
        "title": "Implement Error Recovery System",
        "body": """# Error Recovery Enhancement

## Objective
Create robust error recovery system for pipeline failures.

## Tasks
- [ ] Implement checkpoint system
- [ ] Add retry mechanisms with exponential backoff
- [ ] Create recovery documentation
- [ ] Add partial success handling
- [ ] Implement state persistence
- [ ] Test recovery scenarios

## Acceptance Criteria
- Failed operations can be resumed
- Data consistency maintained
- Clear error reporting
- Progress preserved on failure
- Documentation complete

## Dependencies
- Pipeline Orchestrator

## Priority
High

## Labels
- enhancement
- reliability
- high-priority""",
        "labels": ["enhancement", "reliability", "high-priority"]
    },
    {
        "title": "Add Progress Tracking System",
        "body": """# Progress Tracking Implementation

## Objective
Create comprehensive progress tracking system for pipeline operations.

## Tasks
- [ ] Add progress bar support
- [ ] Create status update system
- [ ] Implement logging dashboard
- [ ] Add performance metrics
- [ ] Create real-time status API
- [ ] Test progress reporting

## Acceptance Criteria
- Real-time progress updates
- Accurate progress reporting
- Performance metrics tracked
- User-friendly progress display
- Documentation complete

## Dependencies
- Pipeline Orchestrator

## Priority
Medium

## Labels
- enhancement
- ui
- monitoring""",
        "labels": ["enhancement", "ui", "monitoring"]
    },
    {
        "title": "Prepare ChromaDB Migration",
        "body": """# ChromaDB Migration Planning

## Objective
Plan and prepare migration from temporary vector store to ChromaDB.

## Tasks
- [ ] Test ChromaDB compatibility
- [ ] Create migration scripts
- [ ] Update vector store interface
- [ ] Add performance tests
- [ ] Document migration process
- [ ] Create rollback plan

## Acceptance Criteria
- ChromaDB compatibility verified
- Migration path documented
- Performance benchmarks completed
- Rollback procedure documented
- Interface updates planned

## Dependencies
- Vector Store Implementation

## Priority
Medium

## Labels
- enhancement
- database
- migration""",
        "labels": ["enhancement", "database", "migration"]
    },
    {
        "title": "Performance Optimization Phase",
        "body": """# Performance Optimization Implementation

## Objective
Optimize pipeline performance and resource usage.

## Tasks
- [ ] Profile current implementation
- [ ] Optimize batch processing
- [ ] Add caching layer
- [ ] Implement parallel processing
- [ ] Create performance benchmarks
- [ ] Document optimization results

## Acceptance Criteria
- Measurable performance improvements
- Resource usage optimized
- Benchmarks documented
- Scaling guidelines created
- Performance test suite added

## Dependencies
- Pipeline Implementation
- Error Recovery System

## Priority
Medium

## Labels
- enhancement
- performance
- optimization""",
        "labels": ["enhancement", "performance", "optimization"]
    }
]

def create_github_issue(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a GitHub issue using the REST API."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.post(url, json=issue_data, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    """Create all defined issues."""
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set")
        return
        
    print(f"Creating {len(ISSUES)} issues...")
    
    for issue in ISSUES:
        try:
            result = create_github_issue(issue)
            print(f"Created issue #{result['number']}: {issue['title']}")
        except Exception as e:
            print(f"Failed to create issue '{issue['title']}': {str(e)}")
            
    print("Done!")

if __name__ == "__main__":
    main()