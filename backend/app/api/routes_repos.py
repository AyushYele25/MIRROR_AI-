"""Repository routes — list repos and get evolution timelines."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    RepoTimelineResponse,
    RepositoryResponse,
    TimelineEvent,
)
from app.db.models import Commit, RepoFeature, Repository, User
from app.db.session import get_db
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["repositories"])


@router.get("/repos/{username}", response_model=list[RepositoryResponse])
async def list_repos(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> list[RepositoryResponse]:
    """List all analyzed repositories for a GitHub user, with feature signals."""
    username = username.strip().lower()

    result = await db.execute(
        select(User).where(User.github_login == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"No data found for {username}")

    repos_result = await db.execute(
        select(Repository)
        .where(Repository.user_id == user.id)
        .options(selectinload(Repository.repo_features))
        .order_by(Repository.stars.desc())
    )
    repos = repos_result.scalars().all()

    response = []
    for repo in repos:
        # Collect latest features into a dict
        features = {}
        for rf in repo.repo_features:
            features[rf.feature_name] = rf.feature_value

        response.append(RepositoryResponse(
            id=repo.id,
            name=repo.name,
            full_name=repo.full_name,
            url=repo.url,
            description=repo.description,
            primary_language=repo.primary_language,
            stars=repo.stars,
            is_fork=repo.is_fork,
            size_kb=repo.size_kb,
            topics=repo.topics if isinstance(repo.topics, list) else None,
            github_created_at=repo.github_created_at,
            features=features,
        ))

    return response


@router.get("/repo/{repo_id}/timeline", response_model=RepoTimelineResponse)
async def get_repo_timeline(
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RepoTimelineResponse:
    """Get the evolution timeline for a repository (the 'archaeology' view)."""
    result = await db.execute(
        select(Repository)
        .where(Repository.id == repo_id)
        .options(selectinload(Repository.commits))
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Build timeline events from commits
    events = []
    for commit in sorted(repo.commits, key=lambda c: c.timestamp):
        # Classify commit type from message
        msg_lower = commit.message.lower()
        if any(kw in msg_lower for kw in ("fix", "bug", "patch", "hotfix")):
            event_type = "bugfix"
        elif any(kw in msg_lower for kw in ("refactor", "cleanup", "reorganize")):
            event_type = "refactor"
        elif any(kw in msg_lower for kw in ("test", "spec", "coverage")):
            event_type = "testing"
        elif any(kw in msg_lower for kw in ("feat", "add", "implement", "new")):
            event_type = "feature"
        elif any(kw in msg_lower for kw in ("doc", "readme", "comment")):
            event_type = "documentation"
        elif any(kw in msg_lower for kw in ("ci", "deploy", "docker", "build")):
            event_type = "devops"
        else:
            event_type = "commit"

        events.append(TimelineEvent(
            timestamp=commit.timestamp,
            event_type=event_type,
            title=commit.message[:120],
            description=None,
            metrics={
                "additions": commit.additions,
                "deletions": commit.deletions,
                "files_changed": commit.files_changed,
            },
            sha=commit.sha,
            source_url=f"{repo.url}/commit/{commit.sha}",
        ))

    return RepoTimelineResponse(
        repo_id=repo.id,
        repo_name=repo.full_name,
        events=events,
    )
