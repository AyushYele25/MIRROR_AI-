"""Test configuration and fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_github_user():
    """Sample GitHub user API response for testing."""
    return {
        "login": "testuser",
        "id": 12345,
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        "bio": "A test user",
        "public_repos": 10,
        "created_at": "2020-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_github_repo():
    """Sample GitHub repo API response for testing."""
    return {
        "id": 67890,
        "name": "test-repo",
        "full_name": "testuser/test-repo",
        "html_url": "https://github.com/testuser/test-repo",
        "description": "A test repository",
        "language": "Python",
        "stargazers_count": 5,
        "forks_count": 1,
        "fork": False,
        "archived": False,
        "default_branch": "main",
        "size": 1024,
        "topics": ["python", "testing"],
        "created_at": "2021-06-15T00:00:00Z",
        "pushed_at": "2024-01-01T00:00:00Z",
        "owner": {"login": "testuser"},
    }


@pytest.fixture
def sample_github_commit():
    """Sample GitHub commit API response for testing."""
    return {
        "sha": "abc123def456789012345678901234567890abcd",
        "commit": {
            "author": {
                "name": "Test User",
                "email": "test@example.com",
                "date": "2024-01-15T10:30:00Z",
            },
            "message": "feat: add user authentication",
        },
        "author": {"login": "testuser"},
        "stats": {
            "additions": 150,
            "deletions": 30,
        },
        "files": [
            {"filename": "auth.py"},
            {"filename": "tests/test_auth.py"},
        ],
    }


@pytest.fixture
def sample_tree_item():
    """Sample GitHub tree item for testing."""
    return {
        "path": "src/main.py",
        "type": "blob",
        "size": 2048,
        "sha": "abcdef1234567890",
    }
