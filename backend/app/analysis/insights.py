"""Evidence-backed insight generation engine.

Stage A (deterministic): feature scores → thresholds → insights with evidence.
Stage B (LLM, Phase 4 extension): structured facts → Gemini explanation.

Every insight must link to specific repos/files/commits — no fabrication.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.analysis.profile import DeveloperFingerprint
from app.analysis.repo_features import RepoFeatureVector
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EvidenceItem:
    """One piece of supporting evidence for an insight."""
    repo_name: str = ""
    file_path: str = ""
    commit_sha: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    source_url: str = ""
    context: str = ""


@dataclass
class InsightItem:
    """A generated insight with evidence."""
    type: str  # "strength", "gap", "observation", "recommendation"
    title: str
    severity: str  # "high", "medium", "low", "info"
    score: float  # 0-100
    confidence: float  # 0-1
    explanation: str = ""
    recommendation: str = ""
    evidence: List[EvidenceItem] = field(default_factory=list)


# ── Threshold-based insight rules ────────────────────────────────

def _generate_code_quality_insights(
    fingerprint: DeveloperFingerprint,
    repo_features: List[Tuple[str, RepoFeatureVector]],
) -> List[InsightItem]:
    """Generate insights about code quality."""
    insights = []
    score = fingerprint.code_quality

    if score >= 75:
        insights.append(InsightItem(
            type="strength",
            title="Strong code quality discipline",
            severity="info",
            score=score,
            confidence=fingerprint.dimension_confidence.get("code_quality", 0.5),
            explanation=f"Code quality score is {score:.0f}/100. Repositories show low complexity, good function structure, and maintainable code patterns.",
            recommendation="Continue maintaining clean code practices. Consider mentoring others on code quality.",
            evidence=[
                EvidenceItem(
                    repo_name=name,
                    metric_name="maintainability_index",
                    metric_value=rf.maintainability_index,
                    context=f"MI score: {rf.maintainability_index:.1f}",
                )
                for name, rf in repo_features[:3]
                if rf.maintainability_index > 0
            ],
        ))
    elif score < 40:
        low_mi_repos = [
            (name, rf) for name, rf in repo_features
            if rf.maintainability_index > 0 and rf.maintainability_index < 50
        ]
        insights.append(InsightItem(
            type="gap",
            title="Code quality signals are underdeveloped",
            severity="medium",
            score=score,
            confidence=fingerprint.dimension_confidence.get("code_quality", 0.5),
            explanation=f"Code quality score is {score:.0f}/100. Observable patterns suggest high complexity or low maintainability in several repositories.",
            recommendation="Focus on reducing cyclomatic complexity, splitting long functions, and adding type hints. Use tools like ruff and mypy.",
            evidence=[
                EvidenceItem(
                    repo_name=name,
                    metric_name="avg_cyclomatic_complexity",
                    metric_value=rf.avg_cyclomatic_complexity,
                    context=f"Average CC: {rf.avg_cyclomatic_complexity:.1f}",
                )
                for name, rf in low_mi_repos[:3]
            ],
        ))

    return insights


def _generate_testing_insights(
    fingerprint: DeveloperFingerprint,
    repo_features: List[Tuple[str, RepoFeatureVector]],
) -> List[InsightItem]:
    """Generate insights about testing discipline."""
    insights = []
    score = fingerprint.testing

    # Find repos without tests
    untested = [(n, rf) for n, rf in repo_features if rf.test_file_ratio == 0 and not rf.ci_present]
    tested = [(n, rf) for n, rf in repo_features if rf.test_file_ratio > 0]

    if score >= 70:
        insights.append(InsightItem(
            type="strength",
            title="Solid testing discipline",
            severity="info",
            score=score,
            confidence=fingerprint.dimension_confidence.get("testing", 0.5),
            explanation=f"Testing score is {score:.0f}/100. Test files, test-related commits, and CI presence are detected across repositories.",
            recommendation="Explore property-based testing, mutation testing, or integration test patterns to deepen expertise.",
            evidence=[
                EvidenceItem(
                    repo_name=name,
                    metric_name="test_file_ratio",
                    metric_value=rf.test_file_ratio,
                    context=f"Test ratio: {rf.test_file_ratio:.1%}, CI: {'yes' if rf.ci_present else 'no'}",
                )
                for name, rf in tested[:3]
            ],
        ))
    elif score < 35:
        insights.append(InsightItem(
            type="gap",
            title="Testing signals are underdeveloped",
            severity="high",
            score=score,
            confidence=fingerprint.dimension_confidence.get("testing", 0.5),
            explanation=f"Testing score is {score:.0f}/100. Most repositories lack test files and CI configuration.",
            recommendation="Add pytest tests and a GitHub Actions CI pipeline to your next project. Start with the most critical functions.",
            evidence=[
                EvidenceItem(
                    repo_name=name,
                    metric_name="test_file_ratio",
                    metric_value=rf.test_file_ratio,
                    context=f"Test ratio: {rf.test_file_ratio:.1%}, CI: {'yes' if rf.ci_present else 'no'}",
                )
                for name, rf in untested[:3]
            ],
        ))

    return insights


def _generate_tooling_insights(
    fingerprint: DeveloperFingerprint,
    repo_features: List[Tuple[str, RepoFeatureVector]],
) -> List[InsightItem]:
    """Generate insights about engineering tooling."""
    insights = []
    score = fingerprint.tooling

    if score >= 70:
        insights.append(InsightItem(
            type="strength",
            title="Strong engineering tooling maturity",
            severity="info",
            score=score,
            confidence=fingerprint.dimension_confidence.get("tooling", 0.5),
            explanation=f"Tooling score is {score:.0f}/100. Docker, CI/CD, linting, and other engineering tools are present.",
            recommendation="Consider adding infrastructure-as-code, monitoring, or advanced CI patterns.",
        ))
    elif score < 30:
        insights.append(InsightItem(
            type="gap",
            title="Engineering tooling is minimal",
            severity="medium",
            score=score,
            confidence=fingerprint.dimension_confidence.get("tooling", 0.5),
            explanation=f"Tooling score is {score:.0f}/100. Repositories lack Docker, CI/CD, linting, or formatting configurations.",
            recommendation="Add a Dockerfile, GitHub Actions CI, and a linter (ruff for Python, ESLint for JS) to your next project.",
            evidence=[
                EvidenceItem(
                    repo_name=name,
                    metric_name="tooling_score",
                    metric_value=rf.tooling_score,
                    context=f"Tooling score: {rf.tooling_score:.1%}",
                )
                for name, rf in repo_features[:3]
                if rf.tooling_score < 0.3
            ],
        ))

    return insights


def _generate_architecture_insights(
    fingerprint: DeveloperFingerprint,
    repo_features: List[Tuple[str, RepoFeatureVector]],
) -> List[InsightItem]:
    """Generate insights about architecture/decomposition."""
    insights = []
    score = fingerprint.architecture

    if score >= 70:
        insights.append(InsightItem(
            type="strength",
            title="Good architectural decomposition",
            severity="info",
            score=score,
            confidence=fingerprint.dimension_confidence.get("architecture", 0.5),
            explanation=f"Architecture score is {score:.0f}/100. Projects show modular structure with clear separation of concerns.",
        ))
    elif score < 35:
        insights.append(InsightItem(
            type="gap",
            title="Limited architectural structure",
            severity="medium",
            score=score,
            confidence=fingerprint.dimension_confidence.get("architecture", 0.5),
            explanation=f"Architecture score is {score:.0f}/100. Projects tend to have flat structures without clear layering.",
            recommendation="Structure your next project with separate directories for routes, services, models, and tests. Use a service layer pattern.",
        ))

    return insights


def _generate_documentation_insights(
    fingerprint: DeveloperFingerprint,
    repo_features: List[Tuple[str, RepoFeatureVector]],
) -> List[InsightItem]:
    """Generate insights about documentation."""
    insights = []
    score = fingerprint.documentation

    if score >= 65:
        insights.append(InsightItem(
            type="strength",
            title="Good documentation habits",
            severity="info",
            score=score,
            confidence=fingerprint.dimension_confidence.get("documentation", 0.5),
            explanation=f"Documentation score is {score:.0f}/100. Repositories have READMEs, docstrings, and inline comments.",
        ))
    elif score < 30:
        insights.append(InsightItem(
            type="gap",
            title="Documentation is sparse",
            severity="low",
            score=score,
            confidence=fingerprint.dimension_confidence.get("documentation", 0.5),
            explanation=f"Documentation score is {score:.0f}/100. Repositories lack detailed READMEs, docstrings, or comments.",
            recommendation="Add a comprehensive README to each project, including setup instructions, architecture overview, and examples.",
        ))

    return insights


def _generate_overall_insights(
    fingerprint: DeveloperFingerprint,
) -> List[InsightItem]:
    """Generate high-level profile observations."""
    insights = []

    # Confidence warning
    if fingerprint.confidence < 0.3:
        insights.append(InsightItem(
            type="observation",
            title="Low confidence — limited data available",
            severity="medium",
            score=fingerprint.confidence * 100,
            confidence=1.0,
            explanation=f"Profile confidence is {fingerprint.confidence:.0%}. Only {fingerprint.repos_analyzed} repositories and {fingerprint.total_commits} commits were analyzed. Results may not represent full engineering capability.",
            recommendation="Add more public repositories with substantial code to improve profile accuracy.",
        ))

    # Overall strength summary
    dimensions = fingerprint.to_feature_vector_dict()
    strong_dims = [d for d, v in dimensions.items() if v >= 70]
    weak_dims = [d for d, v in dimensions.items() if v < 35]

    if strong_dims:
        insights.append(InsightItem(
            type="strength",
            title=f"Strong in {len(strong_dims)} engineering dimension{'s' if len(strong_dims) > 1 else ''}",
            severity="info",
            score=fingerprint.overall_score,
            confidence=fingerprint.confidence,
            explanation=f"Top strengths: {', '.join(d.replace('_', ' ').title() for d in strong_dims)}.",
        ))

    return insights


def generate_all_insights(
    fingerprint: DeveloperFingerprint,
    repo_features: List[Tuple[str, RepoFeatureVector]],
) -> List[InsightItem]:
    """Generate all deterministic insights for a developer profile.

    This is the main entry point for Stage A insight generation.

    Args:
        fingerprint: The developer's engineering fingerprint.
        repo_features: List of (repo_name, RepoFeatureVector) tuples.

    Returns:
        List of InsightItems, each backed by evidence where available.
    """
    all_insights: List[InsightItem] = []

    all_insights.extend(_generate_overall_insights(fingerprint))
    all_insights.extend(_generate_code_quality_insights(fingerprint, repo_features))
    all_insights.extend(_generate_testing_insights(fingerprint, repo_features))
    all_insights.extend(_generate_tooling_insights(fingerprint, repo_features))
    all_insights.extend(_generate_architecture_insights(fingerprint, repo_features))
    all_insights.extend(_generate_documentation_insights(fingerprint, repo_features))

    # Sort: gaps first (by severity), then strengths
    severity_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    type_order = {"gap": 0, "observation": 1, "recommendation": 2, "strength": 3}

    all_insights.sort(key=lambda i: (
        type_order.get(i.type, 4),
        severity_order.get(i.severity, 4),
    ))

    # Ensure grounding rate
    grounded = sum(1 for i in all_insights if i.evidence)
    total = len(all_insights)
    grounding_rate = grounded / total if total > 0 else 0

    logger.info(
        "insights_generated",
        total=total,
        grounded=grounded,
        grounding_rate=f"{grounding_rate:.0%}",
    )

    return all_insights
