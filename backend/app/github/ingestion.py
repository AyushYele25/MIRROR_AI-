"""GitHub ingestion pipeline.

Orchestrates the full flow:
  username → validate profile → list repos → fetch commits → fetch tree
  → normalize → persist to database.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Commit, File, Repository, User
from app.github.client import GitHubClient, GitHubAPIError, GitHubRateLimitError
from app.github.normalizer import (
    normalize_commit,
    normalize_file,
    normalize_repository,
    normalize_user,
)
from app.logging_config import get_logger

logger = get_logger(__name__)


# Source-code extensions worth fetching content for (for AST analysis)
ANALYZABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
    ".rb", ".cpp", ".c", ".cs", ".php", ".swift", ".kt", ".scala",
}

# Configuration files worth fetching (for tooling detection)
CONFIG_FILES = {
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".travis.yml", "jenkinsfile", ".gitlab-ci.yml",
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "tsconfig.json",
    ".eslintrc", ".eslintrc.json", ".eslintrc.js",
    ".prettierrc", ".prettierrc.json",
    "requirements.txt", "pipfile", "poetry.lock",
    "makefile", ".flake8", "mypy.ini", ".mypy.ini",
    "pytest.ini", "tox.ini", ".coveragerc",
    "alembic.ini",
}


def _should_fetch_content(path: str) -> bool:
    """Decide whether to fetch the content of a file."""
    basename = path.rsplit("/", 1)[-1].lower()

    # Always fetch config files
    if basename in CONFIG_FILES:
        return True

    # Fetch README files
    if basename.startswith("readme"):
        return True

    # Fetch CI/CD files
    parts = path.lower().split("/")
    if ".github" in parts and "workflows" in parts:
        return True

    # Fetch source code files
    ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
    if ext.lower() in ANALYZABLE_EXTENSIONS:
        return True

    return False


async def ingest_github_profile(
    username: str,
    db: AsyncSession,
    *,
    progress_callback: Optional[Callable[[float, str], Any]] = None,
) -> User:
    """Full ingestion pipeline for a GitHub user.

    Args:
        username: GitHub username to analyze
        db: Async database session
        progress_callback: Optional async callback(progress: float, step: str)

    Returns:
        The created/updated User record with all repos, commits, files persisted.
    """
    async def report(progress: float, step: str) -> None:
        if progress_callback:
            await progress_callback(progress, step)
        logger.info("ingestion_progress", progress=progress, step=step)

    await report(0.0, "Connecting to GitHub API")

    async with GitHubClient() as client:
        # ── Step 1: Fetch user profile ───────────────────────────
        await report(0.05, "Fetching GitHub profile")
        raw_user = await client.get_user(username)

        # Check if user already exists
        existing = await db.execute(
            select(User).where(User.github_login == username.lower())
        )
        user = existing.scalar_one_or_none()

        if user:
            # Update existing user
            user.display_name = raw_user.get("name") or raw_user["login"]
            user.avatar_url = raw_user.get("avatar_url")
            user.bio = raw_user.get("bio")
            user.public_repos = raw_user.get("public_repos", 0)
            user.updated_at = datetime.now(timezone.utc)
        else:
            user = normalize_user(raw_user)
            db.add(user)

        await db.flush()  # Get the user.id

        # ── Step 2: Fetch repositories ───────────────────────────
        await report(0.10, "Fetching repositories")
        raw_repos = await client.get_user_repos(username)

        if not raw_repos:
            logger.warning("no_repos_found", username=username)
            await db.commit()
            return user

        await report(0.15, f"Found {len(raw_repos)} repositories")

        # ── Step 3: Process each repository ──────────────────────
        total_repos = len(raw_repos)
        for idx, raw_repo in enumerate(raw_repos):
            repo_progress = 0.15 + (0.80 * (idx / total_repos))
            repo_name = raw_repo["name"]
            owner = raw_repo["owner"]["login"]

            await report(
                repo_progress,
                f"Analyzing repository {idx + 1}/{total_repos}: {repo_name}",
            )

            # Check if repo already exists
            existing_repo = await db.execute(
                select(Repository).where(
                    Repository.github_id == raw_repo["id"]
                )
            )
            repo = existing_repo.scalar_one_or_none()

            if repo:
                # Update metadata
                repo.stars = raw_repo.get("stargazers_count", 0)
                repo.size_kb = raw_repo.get("size", 0)
                repo.last_analyzed_at = datetime.now(timezone.utc)
            else:
                repo = normalize_repository(raw_repo, user.id)
                db.add(repo)

            await db.flush()

            # ── Fetch commits ────────────────────────────────────
            try:
                raw_commits = await client.get_repo_commits(
                    owner, repo_name,
                    max_commits=settings.max_commits_per_repo,
                )

                for raw_commit in raw_commits:
                    # Check if commit already exists
                    existing_commit = await db.execute(
                        select(Commit).where(
                            Commit.repo_id == repo.id,
                            Commit.sha == raw_commit["sha"],
                        )
                    )
                    if existing_commit.scalar_one_or_none():
                        continue

                    commit = normalize_commit(raw_commit, repo.id)
                    db.add(commit)

            except GitHubAPIError as e:
                logger.warning(
                    "commit_fetch_failed",
                    repo=repo_name, error=str(e),
                )
            except GitHubRateLimitError:
                logger.warning("rate_limit_hit_during_commits", repo=repo_name)
                break

            # ── Fetch file tree ──────────────────────────────────
            try:
                tree_items = await client.get_repo_tree(
                    owner, repo_name,
                    branch=raw_repo.get("default_branch", "main"),
                )

                # Fetch content for analyzable files (with concurrency limit)
                semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

                async def fetch_and_store_file(item: Dict[str, Any]) -> None:
                    path = item.get("path", "")
                    content = None

                    if _should_fetch_content(path):
                        async with semaphore:
                            content = await client.get_file_content(
                                owner, repo_name, path
                            )
                            # Small delay to be gentle on the API
                            await asyncio.sleep(0.1)

                    file_record = normalize_file(item, repo.id, content)
                    db.add(file_record)

                # Process files in batches
                for i in range(0, len(tree_items), 10):
                    batch = tree_items[i:i + 10]
                    await asyncio.gather(
                        *[fetch_and_store_file(item) for item in batch]
                    )

            except GitHubAPIError as e:
                logger.warning(
                    "tree_fetch_failed",
                    repo=repo_name, error=str(e),
                )
            except GitHubRateLimitError:
                logger.warning("rate_limit_hit_during_tree", repo=repo_name)
                break

            # Flush after each repo
            await db.flush()

        # ── Step 4: Commit everything ────────────────────────────
        await report(0.95, "Saving analysis data")
        await db.commit()
        await report(1.0, "Ingestion complete")

        logger.info(
            "ingestion_complete",
            username=username,
            repos_processed=total_repos,
        )

        return user
