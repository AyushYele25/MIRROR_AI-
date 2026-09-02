"""GitHub data normalizer — converts raw API responses to DB records."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.models import Commit, File, Repository, User
from app.logging_config import get_logger

logger = get_logger(__name__)

# Language detection by extension
LANGUAGE_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".jsx": "JavaScript", ".java": "Java",
    ".cpp": "C++", ".c": "C", ".h": "C", ".hpp": "C++",
    ".cs": "C#", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".php": "PHP", ".swift": "Swift", ".kt": "Kotlin",
    ".scala": "Scala", ".r": "R", ".R": "R",
    ".sql": "SQL", ".sh": "Shell", ".bash": "Shell",
    ".yml": "YAML", ".yaml": "YAML", ".json": "JSON",
    ".xml": "XML", ".html": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".md": "Markdown", ".rst": "reStructuredText",
    ".toml": "TOML", ".ini": "INI", ".cfg": "INI",
    ".dockerfile": "Dockerfile",
    ".tf": "Terraform", ".hcl": "HCL",
    ".ipynb": "Jupyter Notebook",
}


def detect_language(path: str) -> str | None:
    """Detect programming language from file extension."""
    basename = os.path.basename(path).lower()

    # Special filenames
    if basename == "dockerfile":
        return "Dockerfile"
    if basename == "makefile":
        return "Makefile"
    if basename in ("jenkinsfile",):
        return "Groovy"

    _, ext = os.path.splitext(path)
    return LANGUAGE_MAP.get(ext.lower())


def normalize_user(raw: Dict[str, Any]) -> User:
    """Convert raw GitHub user API response to a User model instance."""
    created_at = None
    if raw.get("created_at"):
        try:
            created_at = datetime.fromisoformat(
                raw["created_at"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    return User(
        github_login=raw["login"].lower(),
        display_name=raw.get("name") or raw["login"],
        avatar_url=raw.get("avatar_url"),
        bio=raw.get("bio"),
        public_repos=raw.get("public_repos", 0),
        github_created_at=created_at,
    )


def normalize_repository(raw: Dict[str, Any], user_id: Any) -> Repository:
    """Convert raw GitHub repo API response to a Repository model instance."""
    def parse_dt(val: str | None) -> datetime | None:
        if not val:
            return None
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    return Repository(
        user_id=user_id,
        github_id=raw["id"],
        name=raw["name"],
        full_name=raw["full_name"],
        url=raw["html_url"],
        description=raw.get("description"),
        primary_language=raw.get("language"),
        stars=raw.get("stargazers_count", 0),
        forks_count=raw.get("forks_count", 0),
        is_fork=raw.get("fork", False),
        is_archived=raw.get("archived", False),
        default_branch=raw.get("default_branch", "main"),
        size_kb=raw.get("size", 0),
        topics=raw.get("topics"),
        github_created_at=parse_dt(raw.get("created_at")),
        github_pushed_at=parse_dt(raw.get("pushed_at")),
    )


def normalize_commit(
    raw: Dict[str, Any],
    repo_id: Any,
) -> Commit:
    """Convert raw GitHub commit API response to a Commit model instance."""
    commit_data = raw.get("commit", {})
    author_data = commit_data.get("author", {})
    stats = raw.get("stats", {})

    timestamp = datetime.now(timezone.utc)
    if author_data.get("date"):
        try:
            timestamp = datetime.fromisoformat(
                author_data["date"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    # Get author login from the top-level (not the commit.author nested object)
    author_login = None
    if raw.get("author"):
        author_login = raw["author"].get("login")

    return Commit(
        repo_id=repo_id,
        sha=raw["sha"],
        author_login=author_login,
        author_email=author_data.get("email"),
        timestamp=timestamp,
        message=commit_data.get("message", "")[:2000],  # Cap message length
        additions=stats.get("additions", 0),
        deletions=stats.get("deletions", 0),
        files_changed=len(raw.get("files", [])),
    )


def normalize_file(
    tree_item: Dict[str, Any],
    repo_id: Any,
    content: str | None = None,
) -> File:
    """Convert a Git tree item to a File model instance."""
    path = tree_item.get("path", "")
    filename = os.path.basename(path)
    language = detect_language(path)
    size = tree_item.get("size", 0)

    content_hash = None
    if content:
        content_hash = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    return File(
        repo_id=repo_id,
        path=path,
        filename=filename,
        language=language,
        size_bytes=size,
        content_hash=content_hash,
        content=content,
    )
