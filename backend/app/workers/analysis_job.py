"""Background analysis job runner.

State machine: queued → running → completed | failed

Orchestrates the full pipeline:
  1. GitHub ingestion (fetch repos, commits, files)
  2. Code analysis (AST metrics, file features)
  3. Temporal analysis (commit history features)
  4. Repository feature aggregation
  5. Profile generation (developer fingerprint)
  6. Insight generation (Phase 4 — stub)
"""

from __future__ import annotations

import traceback
from datetime import date, datetime, timezone
from typing import Dict, List

from sqlalchemy import func as sqlfunc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analysis.ast_features import (
    extract_basic_metrics,
    extract_python_metrics,
)
from app.analysis.history import CommitData
from app.analysis.profile import generate_developer_fingerprint
from app.analysis.repo_features import (
    FEATURE_SCHEMA_VERSION,
    RepoFeatureVector,
    generate_repo_features,
)
from app.db.models import (
    AnalysisJob,
    Commit,
    File,
    FileFeature,
    JobStatus,
    Profile,
    RepoFeature,
    Repository,
    User,
)
from app.db.session import async_session_factory
from app.github.ingestion import ingest_github_profile
from app.logging_config import get_logger

logger = get_logger(__name__)


async def _analyze_repository(
    repo: Repository,
    db: AsyncSession,
    target_author: str,
) -> RepoFeatureVector | None:
    """Run full analysis on a single repository.

    Returns the feature vector, or None if analysis fails.
    """
    try:
        # Load files with content
        files_result = await db.execute(
            select(File).where(File.repo_id == repo.id)
        )
        files = files_result.scalars().all()

        # Load commits
        commits_result = await db.execute(
            select(Commit).where(Commit.repo_id == repo.id)
        )
        commits = commits_result.scalars().all()

        # Prepare data for feature extraction
        file_paths = [f.path for f in files]
        file_contents: Dict[str, str] = {}
        for f in files:
            if f.content:
                file_contents[f.path] = f.content

        commit_data = [
            CommitData(
                sha=c.sha,
                timestamp=c.timestamp,
                message=c.message,
                additions=c.additions,
                deletions=c.deletions,
                files_changed=c.files_changed,
                author_login=c.author_login or "",
            )
            for c in commits
        ]

        # ── Per-file AST analysis ────────────────────────────────
        for f in files:
            if not f.content:
                continue

            if f.path.endswith(".py"):
                metrics = extract_python_metrics(f.content, f.path)
            else:
                metrics = extract_basic_metrics(f.content, f.path)

            # Store file features
            file_feature = FileFeature(
                file_id=f.id,
                cyclomatic_complexity=metrics.cyclomatic_complexity,
                function_count=metrics.function_count,
                class_count=metrics.class_count,
                import_count=metrics.import_count,
                comment_ratio=metrics.comment_ratio,
                docstring_ratio=metrics.docstring_ratio,
                is_test_file=metrics.is_test_file,
                maintainability_index=metrics.maintainability_index,
                loc=metrics.loc,
                sloc=metrics.sloc,
                avg_function_length=metrics.avg_function_length,
                max_function_length=metrics.max_function_length,
                halstead_volume=metrics.halstead_volume,
            )
            db.add(file_feature)

        # ── Generate repo feature vector ─────────────────────────
        repo_fv = generate_repo_features(
            file_paths=file_paths,
            file_contents=file_contents,
            commits=commit_data,
            target_author=target_author,
        )

        # ── Persist repo features ────────────────────────────────
        today = date.today()
        for feature_name, feature_value in repo_fv.to_dict().items():
            repo_feature = RepoFeature(
                repo_id=repo.id,
                feature_name=feature_name,
                feature_value=feature_value,
                snapshot_date=today,
                schema_version=FEATURE_SCHEMA_VERSION,
            )
            db.add(repo_feature)

        # Mark repo as analyzed
        repo.last_analyzed_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info(
            "repo_analysis_complete",
            repo=repo.name,
            files=len(files),
            commits=len(commits),
            loc=repo_fv.total_loc,
        )

        return repo_fv

    except Exception as e:
        logger.error(
            "repo_analysis_failed",
            repo=repo.name,
            error=str(e),
            traceback=traceback.format_exc(),
        )
        return None


async def run_analysis_pipeline(job_id: str, username: str) -> None:
    """Execute the full analysis pipeline for a GitHub user.

    This function runs as a background task. It creates its own
    database session to avoid lifecycle issues with the request session.
    """
    logger.info("analysis_job_starting", job_id=job_id, username=username)

    async with async_session_factory() as db:
        try:
            # ── Mark job as running ──────────────────────────────
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

            # Progress callback for ingestion
            async def update_progress(progress: float, step: str) -> None:
                job.progress = progress * 0.40  # Ingestion is 40% of total
                job.current_step = step
                await db.commit()

            # ── Stage 1: GitHub Ingestion (0-40%) ────────────────
            user = await ingest_github_profile(
                username, db, progress_callback=update_progress,
            )

            job.user_id = user.id
            job.progress = 0.40
            job.current_step = "Ingestion complete"

            # Count repos
            repo_count = await db.execute(
                select(sqlfunc.count(Repository.id)).where(
                    Repository.user_id == user.id
                )
            )
            job.repos_found = repo_count.scalar() or 0
            await db.commit()

            # ── Stage 2: Code & Feature Analysis (40-75%) ────────
            repos_result = await db.execute(
                select(Repository).where(Repository.user_id == user.id)
            )
            repos = repos_result.scalars().all()

            repo_feature_vectors: List[RepoFeatureVector] = []

            for idx, repo in enumerate(repos):
                progress = 0.40 + (0.35 * ((idx + 1) / len(repos)))
                job.progress = progress
                job.current_step = f"Analyzing {repo.name} ({idx + 1}/{len(repos)})"
                job.repos_analyzed = idx + 1
                await db.commit()

                repo_fv = await _analyze_repository(repo, db, username)
                if repo_fv:
                    repo_feature_vectors.append(repo_fv)

            # ── Stage 3: Profile Generation (75-90%) ─────────────
            job.progress = 0.75
            job.current_step = "Building developer fingerprint"
            await db.commit()

            fingerprint = generate_developer_fingerprint(repo_feature_vectors)

            # Persist profile
            profile = Profile(
                user_id=user.id,
                version=1,
                feature_vector=fingerprint.to_feature_vector_dict(),
                confidence=fingerprint.confidence,
                repos_analyzed=fingerprint.repos_analyzed,
                total_commits=fingerprint.total_commits,
                total_files=fingerprint.total_files,
            )

            # Check for existing profile, increment version
            existing_profile = await db.execute(
                select(Profile)
                .where(Profile.user_id == user.id)
                .order_by(Profile.version.desc())
                .limit(1)
            )
            prev = existing_profile.scalar_one_or_none()
            if prev:
                profile.version = prev.version + 1

            db.add(profile)
            await db.flush()

            job.progress = 0.90
            job.current_step = "Generating insights"
            await db.commit()

            # ── Stage 4: Insight Generation (90-100%) — stub ─────
            # TODO: Phase 4 — create evidence-backed insights
            # TODO: Phase 4 — LLM explanation generation

            # ── Complete ─────────────────────────────────────────
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.current_step = "Analysis complete"
            job.repos_analyzed = len(repo_feature_vectors)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                "analysis_job_completed",
                job_id=job_id,
                username=username,
                repos_analyzed=len(repo_feature_vectors),
                confidence=fingerprint.confidence,
                overall_score=fingerprint.overall_score,
            )

        except Exception as e:
            logger.error(
                "analysis_job_failed",
                job_id=job_id,
                username=username,
                error=str(e),
                traceback=traceback.format_exc(),
            )

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
