"""Background analysis job runner.

State machine: queued → running → completed | failed

This runs as a FastAPI BackgroundTask. It orchestrates:
  1. GitHub ingestion
  2. Code analysis (Phase 2)
  3. Profile generation (Phase 3)
  4. Insight generation (Phase 4)
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import AnalysisJob, JobStatus, User
from app.db.session import async_session_factory
from app.github.ingestion import ingest_github_profile
from app.logging_config import get_logger

logger = get_logger(__name__)


async def run_analysis_pipeline(job_id: str, username: str) -> None:
    """Execute the full analysis pipeline for a GitHub user.

    This function is designed to run as a background task. It creates its
    own database session to avoid lifecycle issues with the request session.
    """
    logger.info("analysis_job_starting", job_id=job_id, username=username)

    async with async_session_factory() as db:
        try:
            # Mark job as running
            result = await db.execute(
                select(AnalysisJob).where(AnalysisJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error("analysis_job_not_found", job_id=job_id)
                return

            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job.current_step = "Starting GitHub ingestion"
            await db.commit()

            # Progress callback to update job status
            async def update_progress(progress: float, step: str) -> None:
                job.progress = progress * 0.6  # Ingestion is 60% of total
                job.current_step = step
                await db.commit()

            # ── Stage 1: GitHub Ingestion ────────────────────────
            user = await ingest_github_profile(
                username, db, progress_callback=update_progress,
            )

            # Update job with user reference
            job.user_id = user.id
            job.progress = 0.6
            job.current_step = "Ingestion complete, starting analysis"

            # Count repos and set on job
            from sqlalchemy import func as sqlfunc
            from app.db.models import Repository, Commit
            repo_count = await db.execute(
                select(sqlfunc.count(Repository.id)).where(
                    Repository.user_id == user.id
                )
            )
            job.repos_found = repo_count.scalar() or 0
            await db.commit()

            # ── Stage 2: Code Analysis (Phase 2 — stub) ─────────
            job.progress = 0.7
            job.current_step = "Analyzing code structure"
            await db.commit()

            # TODO: Phase 2 — run AST analysis, feature extraction
            # from app.analysis.ast_features import analyze_repo_files
            # from app.analysis.repo_features import generate_repo_features

            # ── Stage 3: Profile Generation (Phase 3 — stub) ────
            job.progress = 0.8
            job.current_step = "Building developer profile"
            await db.commit()

            # TODO: Phase 3 — generate profile, run clustering
            # from app.analysis.profile import generate_profile

            # ── Stage 4: Insight Generation (Phase 4 — stub) ────
            job.progress = 0.9
            job.current_step = "Generating insights"
            await db.commit()

            # TODO: Phase 4 — create evidence-backed insights
            # from app.llm.explain import generate_explanations

            # ── Complete ─────────────────────────────────────────
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.current_step = "Analysis complete"
            job.repos_analyzed = job.repos_found
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                "analysis_job_completed",
                job_id=job_id,
                username=username,
                repos=job.repos_found,
            )

        except Exception as e:
            logger.error(
                "analysis_job_failed",
                job_id=job_id,
                username=username,
                error=str(e),
                traceback=traceback.format_exc(),
            )

            # Mark job as failed
            try:
                result = await db.execute(
                    select(AnalysisJob).where(AnalysisJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = str(e)[:2000]
                    job.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                logger.error("failed_to_update_job_status", job_id=job_id)
