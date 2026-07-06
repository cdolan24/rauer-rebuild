#!/usr/bin/env python3
"""
Shared GitHub API utilities for creating issues.

This module provides common functionality for GitHub API interactions,
eliminating code duplication across issue creation scripts.

Usage:
    from scripts.github_utils import get_github_token, create_issue

    token = get_github_token()
    issue = create_issue(token, "Title", "Body", ["label1", "label2"])

Functions:
    get_github_token: Get GitHub token from environment variable
    create_issue: Create a GitHub issue with title, body, and labels

Constants:
    GITHUB_OWNER: Repository owner username
    GITHUB_REPO: Repository name
    GITHUB_API_URL: GitHub API base URL
"""

import os
import sys
from typing import List, Dict, Optional
import requests


# GitHub repository information
GITHUB_OWNER = "cdolan24"  # GitHub username
GITHUB_REPO = "buddharauer"
GITHUB_API_URL = "https://api.github.com"


def get_github_token() -> str:
    """
    Get GitHub token from environment variable.

    Returns:
        str: GitHub personal access token

    Raises:
        SystemExit: If GITHUB_TOKEN environment variable is not set

    Example:
        >>> token = get_github_token()
        >>> print(f"Token length: {len(token)}")
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ ERROR: GITHUB_TOKEN environment variable not set")
        print("\nTo create a GitHub token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token (classic)'")
        print("3. Select 'repo' scope")
        print("4. Copy the token and set: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)
    return token


def create_issue(
    token: str,
    title: str,
    body: str,
    labels: Optional[List[str]] = None
) -> Dict:
    """
    Create a GitHub issue using the GitHub REST API.

    Args:
        token: GitHub personal access token with repo scope
        title: Issue title (required)
        body: Issue body in markdown format (required)
        labels: List of label names to apply (optional)

    Returns:
        Dict: Response JSON from GitHub API containing issue details including:
            - number: Issue number
            - html_url: URL to the issue
            - state: Issue state (open/closed)
            - title: Issue title
            - body: Issue body

    Raises:
        requests.HTTPError: If API request fails

    Example:
        >>> token = get_github_token()
        >>> issue = create_issue(
        ...     token=token,
        ...     title="Fix bug in PDF extraction",
        ...     body="## Description\\n\\nDetailed bug description...",
        ...     labels=["bug", "priority-high"]
        ... )
        >>> print(f"Created issue #{issue['number']}")
    """
    # Default to empty list if no labels provided
    if labels is None:
        labels = []

    # Construct API URL
    url = f"{GITHUB_API_URL}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"

    # Set up headers with authentication
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Prepare issue data
    data = {
        "title": title,
        "body": body,
        "labels": labels
    }

    # Make API request
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    return response.json()


def batch_create_issues(
    token: str,
    issues: List[Dict[str, any]],
    verbose: bool = True
) -> tuple[List[Dict], List[str]]:
    """
    Create multiple GitHub issues in batch.

    Args:
        token: GitHub personal access token
        issues: List of issue dictionaries with 'title', 'body', and optional 'labels'
        verbose: Print progress messages (default: True)

    Returns:
        tuple: (created_issues, failed_issues) where:
            - created_issues: List of successfully created issue responses
            - failed_issues: List of error messages for failed issues

    Example:
        >>> token = get_github_token()
        >>> issues = [
        ...     {"title": "Issue 1", "body": "Body 1", "labels": ["bug"]},
        ...     {"title": "Issue 2", "body": "Body 2", "labels": ["enhancement"]}
        ... ]
        >>> created, failed = batch_create_issues(token, issues)
        >>> print(f"Created {len(created)} issues, {len(failed)} failed")
    """
    created_issues = []
    failed_issues = []

    for i, issue_data in enumerate(issues, 1):
        try:
            if verbose:
                print(f"[{i}/{len(issues)}] Creating: {issue_data['title'][:50]}...")

            # Extract issue fields
            title = issue_data['title']
            body = issue_data['body']
            labels = issue_data.get('labels', [])

            # Create issue
            result = create_issue(token, title, body, labels)
            created_issues.append(result)

            if verbose:
                print(f"    ✅ Created: #{result['number']} - {result['html_url']}")

        except requests.HTTPError as e:
            error_msg = f"Failed: {issue_data['title']} - {e}"
            failed_issues.append(error_msg)

            if verbose:
                print(f"    ❌ {error_msg}")
                if e.response:
                    print(f"       Status: {e.response.status_code}")
                    print(f"       Error: {e.response.text}")

        except Exception as e:
            error_msg = f"Failed: {issue_data['title']} - {e}"
            failed_issues.append(error_msg)

            if verbose:
                print(f"    ❌ {error_msg}")

    return created_issues, failed_issues


def print_summary(created_issues: List[Dict], failed_issues: List[str]):
    """
    Print a summary of issue creation results.

    Args:
        created_issues: List of successfully created issue responses
        failed_issues: List of error messages for failed issues

    Example:
        >>> print_summary(created_issues, failed_issues)
        ===================================...
        Successfully created: 5 issues
        Failed: 0 issues
        ...
    """
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"✅ Successfully created: {len(created_issues)} issues")
    print(f"❌ Failed: {len(failed_issues)} issues")

    if created_issues:
        print()
        print("Created Issues:")
        for issue in created_issues:
            print(f"  - #{issue['number']}: {issue['title']}")
            print(f"    {issue['html_url']}")

    if failed_issues:
        print()
        print("Failed Issues:")
        for error in failed_issues:
            print(f"  - {error}")

    print()
    print("=" * 70)
