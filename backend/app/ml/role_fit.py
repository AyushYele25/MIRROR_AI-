"""Role-fit engine — compares developer profiles against target-role requirements.

Defines evidence-backed skill profiles for 5 target roles and calculates
gap scores with actionable next-challenge recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.logging_config import get_logger

logger = get_logger(__name__)


# ── Role Definitions ─────────────────────────────────────────────
# Each role maps fingerprint dimensions to target scores (0-100).
# Weights indicate relative importance of each dimension for the role.

@dataclass
class RoleSkill:
    """A skill requirement for a role."""
    dimension: str
    target_score: float  # 0-100, what the role expects
    weight: float  # 0-1, importance for this role
    evidence_hint: str  # What to look for


ROLE_DEFINITIONS: Dict[str, List[RoleSkill]] = {
    "ML Engineer": [
        RoleSkill("ml_workflow", 80, 0.25, "Notebooks, model files, training scripts, evaluation metrics"),
        RoleSkill("code_quality", 70, 0.15, "Clean Python code, good function structure"),
        RoleSkill("testing", 65, 0.15, "Model validation, unit tests, CI pipelines"),
        RoleSkill("tooling", 75, 0.15, "Docker, MLflow, model serving, CI/CD"),
        RoleSkill("architecture", 60, 0.10, "Pipeline structure, modular design"),
        RoleSkill("documentation", 55, 0.10, "Model cards, README, docstrings"),
        RoleSkill("iteration", 50, 0.05, "Experiment tracking, iterative improvement"),
        RoleSkill("debugging", 45, 0.05, "Bug-fix patterns, error handling"),
    ],
    "Data Scientist": [
        RoleSkill("ml_workflow", 85, 0.25, "Notebooks, statistical analysis, visualization"),
        RoleSkill("documentation", 65, 0.15, "Analysis reports, README, markdown"),
        RoleSkill("code_quality", 55, 0.10, "Readable analysis code"),
        RoleSkill("testing", 45, 0.10, "Data validation, sanity checks"),
        RoleSkill("iteration", 60, 0.10, "Exploratory workflow, frequent experiments"),
        RoleSkill("tooling", 50, 0.10, "Jupyter, pandas, environment management"),
        RoleSkill("architecture", 40, 0.10, "Data pipeline design"),
        RoleSkill("debugging", 40, 0.10, "Data quality debugging"),
    ],
    "Software Engineer": [
        RoleSkill("code_quality", 80, 0.20, "Clean code, low complexity, maintainable"),
        RoleSkill("testing", 75, 0.20, "Comprehensive tests, CI, coverage"),
        RoleSkill("architecture", 75, 0.20, "Modular design, separation of concerns"),
        RoleSkill("tooling", 70, 0.15, "Docker, CI/CD, linting, formatting"),
        RoleSkill("debugging", 60, 0.10, "Bug-fix patterns, systematic debugging"),
        RoleSkill("documentation", 55, 0.08, "API docs, README, comments"),
        RoleSkill("iteration", 55, 0.07, "Regular commits, steady velocity"),
    ],
    "Data Engineer": [
        RoleSkill("architecture", 80, 0.25, "Pipeline design, data modeling, layering"),
        RoleSkill("tooling", 80, 0.20, "Docker, orchestration, CI/CD, infrastructure"),
        RoleSkill("code_quality", 70, 0.15, "Reliable, production-grade code"),
        RoleSkill("testing", 65, 0.15, "Pipeline testing, data validation"),
        RoleSkill("debugging", 55, 0.10, "ETL debugging, error recovery"),
        RoleSkill("documentation", 50, 0.08, "Schema docs, README"),
        RoleSkill("iteration", 50, 0.07, "Incremental pipeline development"),
    ],
    "AI Engineer": [
        RoleSkill("ml_workflow", 75, 0.20, "Model integration, inference pipelines"),
        RoleSkill("architecture", 75, 0.20, "System design for AI services"),
        RoleSkill("tooling", 75, 0.20, "Docker, model serving, APIs, CI/CD"),
        RoleSkill("code_quality", 70, 0.15, "Production-quality ML code"),
        RoleSkill("testing", 60, 0.10, "Model testing, integration tests"),
        RoleSkill("documentation", 55, 0.08, "API docs, model documentation"),
        RoleSkill("debugging", 50, 0.07, "Model debugging, performance issues"),
    ],
}


@dataclass
class GapAnalysis:
    """Gap between current profile and target role."""
    dimension: str
    current_score: float
    target_score: float
    weight: float
    gap: float  # positive = need improvement
    gap_severity: str  # "none", "minor", "moderate", "significant"
    evidence_hint: str


@dataclass
class RoleFitResult:
    """Complete role-fit analysis result."""
    role_name: str
    overall_fit_score: float = 0.0  # 0-100
    overall_fit_label: str = ""  # "Excellent", "Good", "Developing", "Early"
    gaps: List[GapAnalysis] = field(default_factory=list)
    strengths: List[GapAnalysis] = field(default_factory=list)
    top_gaps: List[str] = field(default_factory=list)  # Top 3 gap dimensions
    next_challenge: Optional[Dict] = field(default_factory=dict)


@dataclass
class NextChallenge:
    """A recommended project to close skill gaps."""
    title: str
    description: str
    target_gaps: List[str]
    technologies: List[str]
    milestones: List[str]
    difficulty: str  # "beginner", "intermediate", "advanced"


# ── Challenge templates ──────────────────────────────────────────

CHALLENGE_TEMPLATES: Dict[str, NextChallenge] = {
    "testing": NextChallenge(
        title="Build a Test-Driven REST API",
        description="Create a FastAPI service using strict TDD — write tests first, then implement. Add CI with GitHub Actions and measure coverage.",
        target_gaps=["testing", "tooling"],
        technologies=["pytest", "httpx", "GitHub Actions", "coverage.py"],
        milestones=["Set up pytest with fixtures", "Write failing tests for 5 endpoints", "Implement endpoints to pass tests", "Add CI pipeline", "Achieve >80% coverage"],
        difficulty="intermediate",
    ),
    "tooling": NextChallenge(
        title="Containerized Deployment Pipeline",
        description="Dockerize an existing project, add multi-stage builds, create a docker-compose setup, and deploy with CI/CD.",
        target_gaps=["tooling", "architecture"],
        technologies=["Docker", "docker-compose", "GitHub Actions", "Render/Railway"],
        milestones=["Write Dockerfile with multi-stage build", "Create docker-compose for local dev", "Add health checks", "Set up CI/CD pipeline", "Deploy to free tier"],
        difficulty="intermediate",
    ),
    "architecture": NextChallenge(
        title="Modular Service with Clean Architecture",
        description="Refactor or build a project with clear separation of concerns: routes, services, repositories, models. Add dependency injection.",
        target_gaps=["architecture", "code_quality"],
        technologies=["FastAPI", "SQLAlchemy", "Pydantic", "dependency-injector"],
        milestones=["Design module structure", "Implement repository pattern", "Add service layer", "Create API routes", "Write integration tests"],
        difficulty="intermediate",
    ),
    "ml_workflow": NextChallenge(
        title="End-to-End ML Pipeline",
        description="Build a reproducible ML pipeline with data processing, training, evaluation, and model serving. Track experiments.",
        target_gaps=["ml_workflow", "tooling"],
        technologies=["scikit-learn/PyTorch", "MLflow", "DVC", "FastAPI", "Docker"],
        milestones=["Set up data pipeline", "Train model with experiment tracking", "Add evaluation metrics", "Serve model via API", "Dockerize and deploy"],
        difficulty="advanced",
    ),
    "documentation": NextChallenge(
        title="Developer Documentation Overhaul",
        description="Add comprehensive documentation to an existing project: README, API docs, architecture decisions, and docstrings.",
        target_gaps=["documentation"],
        technologies=["MkDocs/Sphinx", "Mermaid diagrams", "OpenAPI/Swagger"],
        milestones=["Write detailed README", "Add docstrings to all public functions", "Create architecture diagram", "Generate API docs", "Add contribution guide"],
        difficulty="beginner",
    ),
    "debugging": NextChallenge(
        title="Resilient Service with Error Handling",
        description="Build a service that gracefully handles failures: retries, circuit breakers, structured logging, and error recovery.",
        target_gaps=["debugging", "code_quality"],
        technologies=["FastAPI", "structlog", "tenacity", "sentry-sdk"],
        milestones=["Add structured logging", "Implement retry logic", "Add error boundaries", "Set up error monitoring", "Write chaos tests"],
        difficulty="intermediate",
    ),
    "code_quality": NextChallenge(
        title="Code Quality Transformation",
        description="Take an existing project and systematically improve its quality: reduce complexity, add type hints, enforce linting, and refactor long functions.",
        target_gaps=["code_quality", "tooling"],
        technologies=["mypy", "ruff", "radon", "pre-commit"],
        milestones=["Add type hints throughout", "Set up pre-commit hooks", "Reduce cyclomatic complexity", "Split long functions", "Measure before/after metrics"],
        difficulty="intermediate",
    ),
}


def _select_challenge(top_gaps: List[str]) -> Dict:
    """Select the best challenge based on top skill gaps."""
    for gap_dim in top_gaps:
        if gap_dim in CHALLENGE_TEMPLATES:
            challenge = CHALLENGE_TEMPLATES[gap_dim]
            return {
                "title": challenge.title,
                "description": challenge.description,
                "target_gaps": challenge.target_gaps,
                "technologies": challenge.technologies,
                "milestones": challenge.milestones,
                "difficulty": challenge.difficulty,
                "reason": f"This project addresses your top gap: {gap_dim.replace('_', ' ').title()}",
            }

    # Default fallback
    return {
        "title": "Full-Stack Portfolio Project",
        "description": "Build and deploy a complete application that demonstrates your engineering skills end-to-end.",
        "target_gaps": top_gaps[:3],
        "technologies": ["FastAPI", "Next.js", "PostgreSQL", "Docker"],
        "milestones": ["Design architecture", "Build backend", "Build frontend", "Add tests", "Deploy"],
        "difficulty": "advanced",
        "reason": "A full-stack project closes multiple gaps simultaneously.",
    }


def _fit_label(score: float) -> str:
    """Convert numeric fit score to human label."""
    if score >= 80:
        return "Excellent Fit"
    elif score >= 60:
        return "Good Fit"
    elif score >= 40:
        return "Developing"
    else:
        return "Early Stage"


def _gap_severity(gap: float) -> str:
    """Classify gap severity."""
    if gap <= 5:
        return "none"
    elif gap <= 15:
        return "minor"
    elif gap <= 30:
        return "moderate"
    else:
        return "significant"


def calculate_role_fit(
    fingerprint_dict: Dict[str, float],
    role_name: str,
) -> RoleFitResult:
    """Calculate how well a developer profile fits a target role.

    Args:
        fingerprint_dict: The 9-dimension fingerprint as a dict.
        role_name: Target role name (must be in ROLE_DEFINITIONS).

    Returns:
        RoleFitResult with overall score, gaps, strengths, and next challenge.
    """
    if role_name not in ROLE_DEFINITIONS:
        available = ", ".join(ROLE_DEFINITIONS.keys())
        raise ValueError(f"Unknown role '{role_name}'. Available: {available}")

    skills = ROLE_DEFINITIONS[role_name]
    result = RoleFitResult(role_name=role_name)

    total_fit = 0.0
    total_weight = 0.0

    for skill in skills:
        current = fingerprint_dict.get(skill.dimension, 0.0)
        gap = max(0, skill.target_score - current)
        fit_ratio = min(current / skill.target_score, 1.0) if skill.target_score > 0 else 1.0

        total_fit += fit_ratio * skill.weight
        total_weight += skill.weight

        analysis = GapAnalysis(
            dimension=skill.dimension,
            current_score=round(current, 1),
            target_score=skill.target_score,
            weight=skill.weight,
            gap=round(gap, 1),
            gap_severity=_gap_severity(gap),
            evidence_hint=skill.evidence_hint,
        )

        if gap > 5:
            result.gaps.append(analysis)
        else:
            result.strengths.append(analysis)

    # Overall fit score
    result.overall_fit_score = round(
        (total_fit / total_weight * 100) if total_weight > 0 else 0, 1
    )
    result.overall_fit_label = _fit_label(result.overall_fit_score)

    # Sort gaps by severity (weighted gap)
    result.gaps.sort(key=lambda g: g.gap * g.weight, reverse=True)
    result.strengths.sort(key=lambda s: s.current_score, reverse=True)

    # Top 3 gap dimensions
    result.top_gaps = [g.dimension for g in result.gaps[:3]]

    # Generate next challenge
    result.next_challenge = _select_challenge(result.top_gaps)

    logger.info(
        "role_fit_calculated",
        role=role_name,
        fit_score=result.overall_fit_score,
        fit_label=result.overall_fit_label,
        n_gaps=len(result.gaps),
    )

    return result


def get_available_roles() -> List[str]:
    """Return list of supported target roles."""
    return list(ROLE_DEFINITIONS.keys())


def get_role_definition(role_name: str) -> List[Dict]:
    """Return the skill requirements for a role as dicts."""
    if role_name not in ROLE_DEFINITIONS:
        return []
    return [
        {
            "dimension": s.dimension,
            "target_score": s.target_score,
            "weight": s.weight,
            "evidence_hint": s.evidence_hint,
        }
        for s in ROLE_DEFINITIONS[role_name]
    ]
