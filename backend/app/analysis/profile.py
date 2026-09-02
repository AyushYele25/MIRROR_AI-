"""Developer profile engine — aggregates repo features into the 8-dimension fingerprint.

Implements:
- Weighted aggregation of repository feature vectors
- Robust normalization (percentile-based scaling to 0-100)
- Confidence estimation based on data volume
- The 8-dimension "engineering fingerprint"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.analysis.repo_features import RepoFeatureVector
from app.logging_config import get_logger

logger = get_logger(__name__)


# ── Dimension definitions ────────────────────────────────────────
# Each fingerprint dimension is a weighted combination of raw features.

DIMENSION_FORMULAS: Dict[str, Dict[str, float]] = {
    "code_quality": {
        "maintainability_index": 0.35,      # Higher MI = better
        "avg_cyclomatic_complexity": -0.25,  # Lower CC = better (negative weight)
        "avg_function_length": -0.15,        # Shorter functions = better
        "duplication_proxy": -0.25,          # Less duplication = better
    },
    "testing": {
        "test_file_ratio": 0.35,
        "test_commit_ratio": 0.25,
        "ci_present": 0.40,
    },
    "architecture": {
        "module_count": 0.20,
        "layering_score": 0.45,
        "dependency_fan_out": 0.15,
        "project_complexity_score": 0.20,
    },
    "documentation": {
        "readme_density": 0.35,
        "docstring_ratio": 0.35,
        "comment_ratio": 0.30,
    },
    "iteration": {
        "commit_frequency_per_week": 0.35,
        "active_days_ratio": 0.35,
        "avg_change_size": 0.30,
    },
    "debugging": {
        "fix_revert_ratio": 0.50,
        "rename_move_ratio": 0.50,
    },
    "tooling": {
        "tooling_score": 0.50,
        "ci_present": 0.30,
        "dependency_management": 0.20,
    },
    "ml_workflow": {
        "ml_workflow_score": 1.0,
    },
}


# ── Reference ranges for normalization ───────────────────────────
# Based on heuristic observations of typical public repos.
# Used to map raw values to 0-100 scale.

FEATURE_RANGES: Dict[str, Tuple[float, float]] = {
    # (min_typical, max_typical) — values are clipped to this range
    "maintainability_index": (20.0, 100.0),
    "avg_cyclomatic_complexity": (1.0, 15.0),
    "avg_function_length": (3.0, 50.0),
    "duplication_proxy": (0.0, 0.3),
    "module_count": (1.0, 15.0),
    "layering_score": (0.0, 1.0),
    "dependency_fan_out": (0.0, 20.0),
    "test_file_ratio": (0.0, 0.4),
    "test_commit_ratio": (0.0, 0.3),
    "ci_present": (0.0, 1.0),
    "readme_density": (0.0, 50.0),
    "docstring_ratio": (0.0, 1.0),
    "comment_ratio": (0.0, 0.3),
    "commit_frequency_per_week": (0.0, 20.0),
    "active_days_ratio": (0.0, 0.7),
    "avg_change_size": (0.0, 500.0),
    "fix_revert_ratio": (0.0, 0.4),
    "rename_move_ratio": (0.0, 0.2),
    "tooling_score": (0.0, 1.0),
    "dependency_management": (0.0, 1.0),
    "ml_workflow_score": (0.0, 1.0),
    "project_complexity_score": (0.0, 1.0),
}


def _normalize_feature(value: float, feature_name: str) -> float:
    """Normalize a raw feature value to 0-100 scale.

    Uses min-max scaling based on reference ranges.
    """
    if feature_name not in FEATURE_RANGES:
        return min(max(value, 0), 100)

    low, high = FEATURE_RANGES[feature_name]
    if high <= low:
        return 50.0

    # Clip to range
    clipped = max(low, min(value, high))

    # Scale to 0-100
    normalized = ((clipped - low) / (high - low)) * 100
    return round(normalized, 2)


def _calculate_repo_weight(repo_features: RepoFeatureVector) -> float:
    """Calculate the quality weight for a repository.

    Repos with more content, commits, and structure get higher weight.
    This prevents one tiny repo from dominating the profile.
    """
    # LOC factor (0-1): more code = more weight
    loc_factor = min(repo_features.total_loc / 2000, 1.0)

    # Commit factor (0-1): more commits = more sustained project
    commit_factor = min(repo_features.total_commits / 50, 1.0)

    # File factor (0-1): more files = more complex project
    file_factor = min(repo_features.total_files / 30, 1.0)

    # Combined weight (avoid zero)
    weight = (loc_factor * 0.4 + commit_factor * 0.35 + file_factor * 0.25)
    return max(weight, 0.1)  # Minimum weight of 0.1


@dataclass
class DeveloperFingerprint:
    """The 8-dimension engineering profile + metadata."""

    # Core dimensions (0-100 scale)
    code_quality: float = 0.0
    testing: float = 0.0
    architecture: float = 0.0
    documentation: float = 0.0
    iteration: float = 0.0
    debugging: float = 0.0
    tooling: float = 0.0
    ml_workflow: float = 0.0

    # Derived
    project_complexity: float = 0.0
    overall_score: float = 0.0

    # Confidence
    confidence: float = 0.0
    repos_analyzed: int = 0
    total_commits: int = 0
    total_files: int = 0
    total_loc: int = 0

    # Per-dimension confidence
    dimension_confidence: Dict[str, float] = field(default_factory=dict)

    # Raw aggregated features (for ML layer)
    raw_features: Dict[str, float] = field(default_factory=dict)

    def to_feature_vector_dict(self) -> Dict[str, float]:
        """Return the 8+1 dimensions as a dict for storage."""
        return {
            "code_quality": self.code_quality,
            "testing": self.testing,
            "architecture": self.architecture,
            "documentation": self.documentation,
            "iteration": self.iteration,
            "debugging": self.debugging,
            "tooling": self.tooling,
            "ml_workflow": self.ml_workflow,
            "project_complexity": self.project_complexity,
        }

    def to_ml_vector(self) -> List[float]:
        """Return as a flat vector for ML algorithms."""
        return [
            self.code_quality,
            self.testing,
            self.architecture,
            self.documentation,
            self.iteration,
            self.debugging,
            self.tooling,
            self.ml_workflow,
            self.project_complexity,
        ]


def _estimate_confidence(
    repos_analyzed: int,
    total_commits: int,
    total_files: int,
    total_loc: int,
) -> float:
    """Estimate profile confidence on 0-1 scale.

    Based on how much data we have to work with.
    More repos, commits, and code → higher confidence.
    """
    # Repo factor: 5+ repos is high confidence
    repo_factor = min(repos_analyzed / 5, 1.0)

    # Commit factor: 100+ commits is high confidence
    commit_factor = min(total_commits / 100, 1.0)

    # File factor: 50+ files is high confidence
    file_factor = min(total_files / 50, 1.0)

    # LOC factor: 5000+ LOC is high confidence
    loc_factor = min(total_loc / 5000, 1.0)

    # Weighted combination
    confidence = (
        repo_factor * 0.35 +
        commit_factor * 0.30 +
        file_factor * 0.20 +
        loc_factor * 0.15
    )

    return round(confidence, 3)


def generate_developer_fingerprint(
    repo_features_list: List[RepoFeatureVector],
) -> DeveloperFingerprint:
    """Generate the developer engineering fingerprint from repository features.

    This is the main profile generation entry point.

    Args:
        repo_features_list: Feature vectors from all analyzed repositories.

    Returns:
        DeveloperFingerprint with 8 normalized dimensions + confidence.
    """
    fingerprint = DeveloperFingerprint()

    if not repo_features_list:
        return fingerprint

    fingerprint.repos_analyzed = len(repo_features_list)

    # ── Step 1: Weighted aggregation of raw features ─────────────
    weights = [_calculate_repo_weight(rf) for rf in repo_features_list]
    total_weight = sum(weights)

    if total_weight <= 0:
        return fingerprint

    # Aggregate each raw feature as weighted mean
    all_feature_names = set()
    for rf in repo_features_list:
        all_feature_names.update(rf.to_dict().keys())

    aggregated: Dict[str, float] = {}
    for feature_name in all_feature_names:
        weighted_sum = 0.0
        for rf, w in zip(repo_features_list, weights):
            value = rf.to_dict().get(feature_name, 0.0)
            weighted_sum += value * w
        aggregated[feature_name] = weighted_sum / total_weight

    fingerprint.raw_features = aggregated

    # Totals
    fingerprint.total_commits = sum(rf.total_commits for rf in repo_features_list)
    fingerprint.total_files = sum(rf.total_files for rf in repo_features_list)
    fingerprint.total_loc = sum(rf.total_loc for rf in repo_features_list)

    # ── Step 2: Normalize features to 0-100 ──────────────────────
    normalized: Dict[str, float] = {}
    for feature_name, value in aggregated.items():
        normalized[feature_name] = _normalize_feature(value, feature_name)

    # ── Step 3: Calculate dimensions ─────────────────────────────
    for dimension_name, formula in DIMENSION_FORMULAS.items():
        score = 0.0
        total_dim_weight = 0.0

        for feature_name, weight in formula.items():
            feat_value = normalized.get(feature_name, 0.0)

            if weight < 0:
                # Negative weight means inverse relationship
                # (lower raw value = higher score)
                feat_value = 100.0 - feat_value
                weight = abs(weight)

            score += feat_value * weight
            total_dim_weight += weight

        if total_dim_weight > 0:
            dimension_score = score / total_dim_weight
        else:
            dimension_score = 0.0

        # Clamp to 0-100
        dimension_score = max(0, min(100, round(dimension_score, 1)))
        setattr(fingerprint, dimension_name, dimension_score)

    # Project complexity (pass-through from aggregated)
    fingerprint.project_complexity = round(
        aggregated.get("project_complexity_score", 0.0) * 100, 1
    )

    # ── Step 4: Overall score (weighted average of dimensions) ───
    dimension_weights = {
        "code_quality": 0.15,
        "testing": 0.15,
        "architecture": 0.15,
        "debugging": 0.15,
        "documentation": 0.10,
        "tooling": 0.10,
        "project_complexity": 0.10,
        "ml_workflow": 0.10,
    }

    overall = 0.0
    for dim, w in dimension_weights.items():
        overall += getattr(fingerprint, dim, 0.0) * w

    fingerprint.overall_score = round(overall, 1)

    # ── Step 5: Confidence estimation ────────────────────────────
    fingerprint.confidence = _estimate_confidence(
        fingerprint.repos_analyzed,
        fingerprint.total_commits,
        fingerprint.total_files,
        fingerprint.total_loc,
    )

    # Per-dimension confidence (rough: based on data availability)
    for dim_name, formula in DIMENSION_FORMULAS.items():
        has_data = sum(
            1 for feat in formula
            if aggregated.get(feat, 0) > 0
        )
        dim_conf = has_data / len(formula) if formula else 0.0
        fingerprint.dimension_confidence[dim_name] = round(
            dim_conf * fingerprint.confidence, 3
        )

    logger.info(
        "fingerprint_generated",
        repos=fingerprint.repos_analyzed,
        confidence=fingerprint.confidence,
        overall=fingerprint.overall_score,
        code_quality=fingerprint.code_quality,
        testing=fingerprint.testing,
        architecture=fingerprint.architecture,
    )

    return fingerprint
