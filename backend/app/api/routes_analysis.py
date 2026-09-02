"""Analysis routes — start and track GitHub profile analysis."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    AnalysisStatusResponse,
    AnalyzeGitHubRequest,
    AnalyzeGitHubResponse,
)
from app.db.models import AnalysisJob, JobStatus, User
from app.db.session import get_db
from app.logging_config import get_logger
from app.workers.analysis_job import run_analysis_pipeline

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze/github", response_model=AnalyzeGitHubResponse)
async def start_analysis(
    request: AnalyzeGitHubRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeGitHubResponse:
    """Start an analysis job for a public GitHub profile.

    Returns a job_id immediately. The client polls GET /api/analysis/{job_id}
    for progress.
    """
    username = request.github_username.strip().lower()
    logger.info("analysis_requested", github_username=username)

    # Check if there's already a running job for this user
    existing = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.github_username == username)
        .where(AnalysisJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
    )
    existing_job = existing.scalar_one_or_none()
    if existing_job:
        return AnalyzeGitHubResponse(
            job_id=existing_job.id,
            status=existing_job.status.value,
            message=f"Analysis already in progress for {username}",
        )

    # Create new job
    job = AnalysisJob(
        id=uuid.uuid4(),
        github_username=username,
        status=JobStatus.QUEUED,
        progress=0.0,
        current_step="Queued for analysis",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue background analysis
    background_tasks.add_task(run_analysis_pipeline, str(job.id), username)

    logger.info("analysis_job_created", job_id=str(job.id), username=username)

    return AnalyzeGitHubResponse(
        job_id=job.id,
        status=job.status.value,
        message=f"Analysis queued for {username}",
    )


@router.get("/analysis/{job_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisStatusResponse:
    """Poll the status of an analysis job."""
    result = await db.execute(
        select(AnalysisJob).where(AnalysisJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    return AnalysisStatusResponse(
        job_id=job.id,
        status=job.status.value,
        progress=job.progress,
        current_step=job.current_step,
        github_username=job.github_username,
        repos_found=job.repos_found,
        repos_analyzed=job.repos_analyzed,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )
