"""GitHub REST API client with rate limiting, pagination and caching.

Design principles:
- Always respect rate limits (check headers, back off when needed)
- Paginate automatically (up to configurable limits)
- Return typed dicts, not raw httpx responses
- Log all API interactions for debugging
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Files/directories to exclude from code-quality analysis
EXCLUDED_PATHS = {
    "node_modules", ".git", "__pycache__", ".tox", ".mypy_cache",
    ".pytest_cache", "venv", ".venv", "env", "dist", "build",
    ".next", ".nuxt", "vendor", "third_party", "assets", "static",
    ".idea", ".vscode", "coverage", "htmlcov",
}

EXCLUDED_EXTENSIONS = {
    ".lock", ".min.js", ".min.css", ".map", ".woff", ".woff2",
    ".ttf", ".eot", ".ico", ".png", ".jpg", ".jpeg", ".gif",
    ".svg", ".mp4", ".webm", ".pdf", ".zip", ".tar", ".gz",
    ".exe", ".dll", ".so", ".dylib", ".pyc", ".pyo",
}


class GitHubRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""
    def __init__(self, reset_at: datetime, remaining: int = 0):
        self.reset_at = reset_at
        self.remaining = remaining
        seconds = max(0, (reset_at - datetime.now(timezone.utc)).total_seconds())
        super().__init__(
            f"GitHub API rate limit exceeded. Resets in {int(seconds)}s "
            f"at {reset_at.isoformat()}"
        )


class GitHubAPIError(Exception):
    """General GitHub API error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"GitHub API error {status_code}: {message}")


class GitHubClient:
    """Async GitHub REST API client.

    Usage:
        async with GitHubClient() as client:
            user = await client.get_user("octocat")
            repos = await client.get_user_repos("octocat")
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.token = token or settings.github_token
        self._rate_limit_remaining: int = 5000
        self._rate_limit_reset: datetime = datetime.now(timezone.utc)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> GitHubClient:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MIRROR-AI/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _update_rate_limit(self, response: httpx.Response) -> None:
        """Extract rate limit info from response headers."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_ts = response.headers.get("X-RateLimit-Reset")

        if remaining is not None:
            self._rate_limit_remaining = int(remaining)
        if reset_ts is not None:
            self._rate_limit_reset = datetime.fromtimestamp(
                int(reset_ts), tz=timezone.utc
            )

        if self._rate_limit_remaining < 100:
            logger.warning(
                "github_rate_limit_low",
                remaining=self._rate_limit_remaining,
                reset_at=self._rate_limit_reset.isoformat(),
            )

    async def _check_rate_limit(self) -> None:
        """Proactively check if we should wait."""
        if self._rate_limit_remaining <= 5:
            wait_seconds = max(
                0,
                (self._rate_limit_reset - datetime.now(timezone.utc)).total_seconds()
            )
            if wait_seconds > 0:
                raise GitHubRateLimitError(
                    reset_at=self._rate_limit_reset,
                    remaining=self._rate_limit_remaining,
                )

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Make a rate-limit-aware API request."""
        assert self._client is not None, "Client not initialized. Use 'async with'."

        await self._check_rate_limit()

        response = await self._client.request(method, path, **kwargs)
        self._update_rate_limit(response)

        if response.status_code == 403 and self._rate_limit_remaining == 0:
            raise GitHubRateLimitError(
                reset_at=self._rate_limit_reset,
                remaining=0,
            )

        if response.status_code == 404:
            raise GitHubAPIError(404, f"Not found: {path}")

        if response.status_code >= 400:
            raise GitHubAPIError(
                response.status_code,
                response.text[:500],
            )

        return response

    async def _get_json(self, path: str, **kwargs: Any) -> Any:
        """GET request returning parsed JSON."""
        response = await self._request("GET", path, **kwargs)
        return response.json()

    async def _get_paginated(
        self,
        path: str,
        *,
        per_page: int = 100,
        max_items: int = 1000,
        params: dict | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all pages of a paginated endpoint."""
        all_items: List[Dict[str, Any]] = []
        page = 1
        _params = params or {}

        while len(all_items) < max_items:
            _params.update({"per_page": per_page, "page": page})
            response = await self._request("GET", path, params=_params)
            items = response.json()

            if not items or not isinstance(items, list):
                break

            all_items.extend(items)
            page += 1

            # Check if there are more pages via Link header
            link_header = response.headers.get("Link", "")
            if 'rel="next"' not in link_header:
                break

        return all_items[:max_items]

    # ── Public API Methods ───────────────────────────────────────

    async def get_user(self, username: str) -> Dict[str, Any]:
        """Fetch a GitHub user profile."""
        logger.info("github_fetch_user", username=username)
        return await self._get_json(f"/users/{username}")

    async def get_user_repos(
        self,
        username: str,
        *,
        max_repos: int | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all public repositories for a user."""
        max_repos = max_repos or settings.max_repos_per_user
        logger.info("github_fetch_repos", username=username, max_repos=max_repos)

        repos = await self._get_paginated(
            f"/users/{username}/repos",
            max_items=max_repos * 2,  # Fetch extra to filter
            params={"type": "owner", "sort": "pushed"},
        )

        # Filter: exclude forks and archived repos by default
        filtered = [
            r for r in repos
            if not r.get("fork", False) and not r.get("archived", False)
        ]

        # Sort by a quality heuristic: pushed_at recency + has source code
        filtered.sort(
            key=lambda r: (
                r.get("size", 0) > 0,           # Has content
                r.get("pushed_at", ""),           # Recently pushed
            ),
            reverse=True,
        )

        return filtered[:max_repos]

    async def get_repo_commits(
        self,
        owner: str,
        repo: str,
        *,
        max_commits: int | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch commit history for a repository."""
        max_commits = max_commits or settings.max_commits_per_repo
        logger.info(
            "github_fetch_commits",
            owner=owner, repo=repo, max_commits=max_commits,
        )
        return await self._get_paginated(
            f"/repos/{owner}/{repo}/commits",
            max_items=max_commits,
        )

    async def get_commit_detail(
        self, owner: str, repo: str, sha: str
    ) -> Dict[str, Any]:
        """Fetch detailed commit info (with file stats)."""
        return await self._get_json(f"/repos/{owner}/{repo}/commits/{sha}")

    async def get_repo_tree(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
    ) -> List[Dict[str, Any]]:
        """Fetch the file tree of a repository (recursive)."""
        logger.info(
            "github_fetch_tree",
            owner=owner, repo=repo, branch=branch,
        )
        try:
            data = await self._get_json(
                f"/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"},
            )
        except GitHubAPIError as e:
            if e.status_code == 404 and branch == "main":
                # Retry with "master" branch
                data = await self._get_json(
                    f"/repos/{owner}/{repo}/git/trees/master",
                    params={"recursive": "1"},
                )
            else:
                raise

        tree = data.get("tree", [])

        # Filter out excluded paths and binary files
        filtered = []
        for item in tree:
            if item.get("type") != "blob":
                continue

            path = item.get("path", "")
            parts = path.split("/")

            # Skip excluded directories
            if any(part in EXCLUDED_PATHS for part in parts):
                continue

            # Skip excluded extensions
            ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            if ext.lower() in EXCLUDED_EXTENSIONS:
                continue

            # Skip files too large
            size = item.get("size", 0)
            if size > settings.max_file_size_bytes:
                continue

            filtered.append(item)

        return filtered[:settings.max_files_per_repo]

    async def get_file_content(
        self, owner: str, repo: str, path: str
    ) -> str | None:
        """Fetch the raw content of a file."""
        try:
            response = await self._request(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                headers={"Accept": "application/vnd.github.v3.raw"},
            )
            return response.text
        except (GitHubAPIError, Exception) as e:
            logger.debug("github_file_content_failed", path=path, error=str(e))
            return None

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Check current rate limit status."""
        return await self._get_json("/rate_limit")

    @property
    def rate_limit_remaining(self) -> int:
        return self._rate_limit_remaining

    @property
    def rate_limit_reset(self) -> datetime:
        return self._rate_limit_reset
