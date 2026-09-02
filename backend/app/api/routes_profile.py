"""Profile routes — retrieve developer engineering profiles."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    EvidenceResponse,
    FeatureVector,
    InsightResponse,
    ProfileResponse,
)
from app.db.models import Evidence, Insight, Profile, User
from app.db.session import get_db
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile/{username}", response_model=ProfileResponse)
async def get_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Return the latest engineering profile for a GitHub user."""
    username = username.strip().lower()

    # Fetch user
    result = await db.execute(
        select(User).where(User.github_login == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"No profile found for {username}")

    # Fetch latest profile with insights and evidence
    profile_result = await db.execute(
        select(Profile)
        .where(Profile.user_id == user.id)
        .options(
            selectinload(Profile.insights).selectinload(Insight.evidence)
        )
        .order_by(Profile.version.desc())
        .limit(1)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Profile for {username} exists but has not been analyzed yet",
        )

    # Build feature vector from JSONB
    fv_data = profile.feature_vector or {}
    feature_vector = FeatureVector(**{
        k: fv_data.get(k, 0.0)
        for k in FeatureVector.model_fields.keys()
    })

    # Build insights
    insights = []
    for insight in profile.insights:
        evidence_list = [
            EvidenceResponse(
                id=e.id,
                metric_name=e.metric_name,
                metric_value=e.metric_value,
                source_url=e.source_url,
                context=e.context,
            )
            for e in insight.evidence
        ]
        insights.append(InsightResponse(
            id=insight.id,
            type=insight.type.value,
            title=insight.title,
            severity=insight.severity.value,
            score=insight.score,
            confidence=insight.confidence,
            explanation=insight.explanation,
            recommendation=insight.recommendation,
            evidence=evidence_list,
        ))

    return ProfileResponse(
        profile_id=profile.id,
        user_id=user.id,
        github_login=user.github_login,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        version=profile.version,
        feature_vector=feature_vector,
        confidence=profile.confidence,
        repos_analyzed=profile.repos_analyzed,
        total_commits=profile.total_commits,
        total_files=profile.total_files,
        created_at=profile.created_at,
        insights=insights,
    )


@router.delete("/profile/{username}")
async def delete_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete all stored analysis data for a user (privacy endpoint)."""
    username = username.strip().lower()

    result = await db.execute(
        select(User).where(User.github_login == username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"No data found for {username}")

    await db.delete(user)  # CASCADE deletes all related data
    await db.commit()

    logger.info("profile_deleted", username=username)
    return {"message": f"All data for {username} has been deleted"}
