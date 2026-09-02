"""Role-fit and insights routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    EvidenceResponse,
    GapDetail,
    InsightResponse,
    RoleFitRequest,
    RoleFitResponse,
)
from app.db.models import GapResult, Insight, Profile, RoleProfile, User
from app.db.session import get_db
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["roles"])


@router.post("/role-fit", response_model=RoleFitResponse)
async def calculate_role_fit(
    request: RoleFitRequest,
    db: AsyncSession = Depends(get_db),
) -> RoleFitResponse:
    """Calculate how well a developer profile fits a target role."""
    username = request.github_username.strip().lower()

    # Get user and latest profile
    user_result = await db.execute(
        select(User).where(User.github_login == username)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"No profile for {username}")

    profile_result = await db.execute(
        select(Profile)
        .where(Profile.user_id == user.id)
        .order_by(Profile.version.desc())
        .limit(1)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not yet analyzed")

    # Get role profile
    role_result = await db.execute(
        select(RoleProfile)
        .where(RoleProfile.role_name == request.target_role)
    )
    role_skills = role_result.scalars().all()
    if not role_skills:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown role: {request.target_role}. "
                   f"Supported: ML Engineer, Data Scientist, Software Engineer, "
                   f"Data Engineer, AI Engineer",
        )

    # Calculate gaps
    fv = profile.feature_vector or {}
    gaps = []
    total_fit = 0.0
    total_weight = 0.0

    for skill in role_skills:
        current = fv.get(skill.skill, 0.0)
        target = skill.weight * 100  # Scale to 0-100
        gap = max(0, target - current)
        fit_ratio = min(current / target, 1.0) if target > 0 else 1.0

        total_fit += fit_ratio * skill.weight
        total_weight += skill.weight

        gaps.append(GapDetail(
            skill=skill.skill,
            current_score=round(current, 1),
            target_score=round(target, 1),
            gap=round(gap, 1),
        ))

        # Persist gap result
        gap_record = GapResult(
            profile_id=profile.id,
            role_name=request.target_role,
            skill=skill.skill,
            current_score=current,
            target_score=target,
            gap=gap,
        )
        db.add(gap_record)

    overall_fit = round((total_fit / total_weight * 100) if total_weight > 0 else 0, 1)

    await db.commit()

    # Sort gaps by largest gap first
    gaps.sort(key=lambda g: g.gap, reverse=True)

    return RoleFitResponse(
        profile_id=profile.id,
        github_login=username,
        target_role=request.target_role,
        overall_fit_score=overall_fit,
        gaps=gaps,
    )


@router.get("/insights/{profile_id}", response_model=list[InsightResponse])
async def get_insights(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[InsightResponse]:
    """Return all evidence-backed insights for a profile."""
    result = await db.execute(
        select(Insight)
        .where(Insight.profile_id == profile_id)
        .options(selectinload(Insight.evidence))
        .order_by(Insight.score.desc())
    )
    insights = result.scalars().all()

    if not insights:
        raise HTTPException(
            status_code=404,
            detail="No insights found for this profile",
        )

    return [
        InsightResponse(
            id=i.id,
            type=i.type.value,
            title=i.title,
            severity=i.severity.value,
            score=i.score,
            confidence=i.confidence,
            explanation=i.explanation,
            recommendation=i.recommendation,
            evidence=[
                EvidenceResponse(
                    id=e.id,
                    metric_name=e.metric_name,
                    metric_value=e.metric_value,
                    source_url=e.source_url,
                    context=e.context,
                )
                for e in i.evidence
            ],
        )
        for i in insights
    ]
