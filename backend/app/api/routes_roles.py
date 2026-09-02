"""Role-fit and insights routes — now using the ML engine."""

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
from app.db.models import GapResult, Insight, Profile, User
from app.db.session import get_db
from app.logging_config import get_logger
from app.ml.role_fit import calculate_role_fit, get_available_roles

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["roles"])


@router.post("/role-fit", response_model=RoleFitResponse)
async def role_fit_endpoint(
    request: RoleFitRequest,
    db: AsyncSession = Depends(get_db),
) -> RoleFitResponse:
    """Calculate how well a developer profile fits a target role.

    Uses the ML role-fit engine with 5 predefined target roles.
    Returns gap analysis, strengths, and next-challenge recommendation.
    """
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

    # Validate role
    available = get_available_roles()
    if request.target_role not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown role: {request.target_role}. "
                   f"Available: {', '.join(available)}",
        )

    # Calculate role fit using ML engine
    fv = profile.feature_vector or {}
    try:
        result = calculate_role_fit(fv, request.target_role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build response gaps
    gaps = []
    for gap_analysis in result.gaps + result.strengths:
        gaps.append(GapDetail(
            skill=gap_analysis.dimension,
            current_score=gap_analysis.current_score,
            target_score=gap_analysis.target_score,
            gap=gap_analysis.gap,
        ))

        # Persist gap result
        gap_record = GapResult(
            profile_id=profile.id,
            role_name=request.target_role,
            skill=gap_analysis.dimension,
            current_score=gap_analysis.current_score,
            target_score=gap_analysis.target_score,
            gap=gap_analysis.gap,
        )
        db.add(gap_record)

    await db.commit()

    gaps.sort(key=lambda g: g.gap, reverse=True)

    return RoleFitResponse(
        profile_id=profile.id,
        github_login=username,
        target_role=request.target_role,
        overall_fit_score=result.overall_fit_score,
        gaps=gaps,
    )


@router.get("/role-fit/roles")
async def list_available_roles():
    """List all available target roles for role-fit analysis."""
    return {"roles": get_available_roles()}


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
