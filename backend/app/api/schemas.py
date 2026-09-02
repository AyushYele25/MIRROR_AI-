"""Pydantic schemas for API request/response validation.

Kept strictly separate from SQLAlchemy models — never return ORM objects
directly from endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Analysis ─────────────────────────────────────────────────────

class AnalyzeGitHubRequest(BaseModel):
    """POST /api/analyze/github body."""
    github_username: str = Field(
        ..., min_length=1, max_length=39,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$",
        description="Public GitHub username to analyze",
    )


class AnalyzeGitHubResponse(BaseModel):
    """Response from starting an analysis job."""
    job_id: uuid.UUID
    status: str
    message: str


class AnalysisStatusResponse(BaseModel):
    """GET /api/analysis/{job_id} response."""
    job_id: uuid.UUID
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    current_step: Optional[str] = None
    github_username: str
    repos_found: int = 0
    repos_analyzed: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ── Profile ──────────────────────────────────────────────────────

class ProfileSummary(BaseModel):
    """Compact profile for listing."""
    user_id: uuid.UUID
    github_login: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    confidence: float
    repos_analyzed: int
    created_at: datetime


class FeatureVector(BaseModel):
    """The 8-dimension engineering fingerprint."""
    code_quality: float = 0.0
    testing: float = 0.0
    architecture: float = 0.0
    documentation: float = 0.0
    iteration: float = 0.0
    debugging: float = 0.0
    tooling: float = 0.0
    ml_workflow: float = 0.0
    project_complexity: float = 0.0


class ProfileResponse(BaseModel):
    """GET /api/profile/{username} response."""
    profile_id: uuid.UUID
    user_id: uuid.UUID
    github_login: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    version: int
    feature_vector: FeatureVector
    confidence: float
    repos_analyzed: int
    total_commits: int
    total_files: int
    created_at: datetime
    insights: List[InsightResponse] = []


# ── Repositories ─────────────────────────────────────────────────

class RepositoryResponse(BaseModel):
    """Repository with analysis signals."""
    id: uuid.UUID
    name: str
    full_name: str
    url: str
    description: Optional[str] = None
    primary_language: Optional[str] = None
    stars: int = 0
    is_fork: bool = False
    size_kb: int = 0
    topics: Optional[List[str]] = None
    github_created_at: Optional[datetime] = None
    features: Dict[str, float] = {}


class TimelineEvent(BaseModel):
    """A point on the repository evolution timeline."""
    timestamp: datetime
    event_type: str  # commit, refactor, architecture_change, etc.
    title: str
    description: Optional[str] = None
    metrics: Dict[str, Any] = {}
    sha: Optional[str] = None
    source_url: Optional[str] = None


class RepoTimelineResponse(BaseModel):
    """GET /api/repo/{repo_id}/timeline response."""
    repo_id: uuid.UUID
    repo_name: str
    events: List[TimelineEvent] = []
    architecture_snapshots: List[Dict[str, Any]] = []


# ── Insights ─────────────────────────────────────────────────────

class EvidenceResponse(BaseModel):
    """One piece of evidence supporting an insight."""
    id: uuid.UUID
    metric_name: str
    metric_value: float
    repo_name: Optional[str] = None
    file_path: Optional[str] = None
    commit_sha: Optional[str] = None
    source_url: Optional[str] = None
    context: Optional[str] = None


class InsightResponse(BaseModel):
    """An evidence-backed insight."""
    id: uuid.UUID
    type: str
    title: str
    severity: str
    score: float
    confidence: float
    explanation: Optional[str] = None
    recommendation: Optional[str] = None
    evidence: List[EvidenceResponse] = []


# ── Role Fit ─────────────────────────────────────────────────────

class RoleFitRequest(BaseModel):
    """POST /api/role-fit body."""
    github_username: str
    target_role: str = Field(
        ..., description="e.g. 'ML Engineer', 'Data Scientist', 'Software Engineer'"
    )


class GapDetail(BaseModel):
    """One skill gap detail."""
    skill: str
    current_score: float
    target_score: float
    gap: float


class RoleFitResponse(BaseModel):
    """POST /api/role-fit response."""
    profile_id: uuid.UUID
    github_login: str
    target_role: str
    overall_fit_score: float
    gaps: List[GapDetail] = []
    next_challenge: Optional[Dict[str, Any]] = None


# ── Health ───────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """GET /api/health response."""
    status: str = "healthy"
    version: str = "0.1.0"
    environment: str = "development"
    database: str = "unknown"
