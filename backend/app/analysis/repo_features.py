"""Repository-level feature aggregation.

Combines AST metrics, history metrics, and architecture metrics
into a single repo feature vector with 23+ measurable features.

Feature schema version: 1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

from app.analysis.ast_features import (
    FileMetrics,
    detect_tools,
    extract_basic_metrics,
    extract_python_metrics,
    is_ci_config,
    is_test_file,
)
from app.analysis.architecture import ArchitectureMetrics, analyze_architecture
from app.analysis.history import CommitData, HistoryMetrics, extract_history_metrics
from app.logging_config import get_logger

logger = get_logger(__name__)

# Current feature schema version — bump when formulas change
FEATURE_SCHEMA_VERSION = 1


@dataclass
class RepoFeatureVector:
    """Complete feature vector for a single repository.

    All 23+ measurable features from the implementation plan.
    """
    # ── Code Quality ─────────────────────────────────────────────
    avg_cyclomatic_complexity: float = 0.0
    avg_function_length: float = 0.0
    duplication_proxy: float = 0.0
    maintainability_index: float = 0.0

    # ── Architecture ─────────────────────────────────────────────
    module_count: int = 0
    dependency_fan_out: float = 0.0
    layering_score: float = 0.0

    # ── Testing ──────────────────────────────────────────────────
    test_file_ratio: float = 0.0
    test_commit_ratio: float = 0.0
    ci_present: bool = False

    # ── Documentation ────────────────────────────────────────────
    readme_density: float = 0.0
    docstring_ratio: float = 0.0
    comment_ratio: float = 0.0

    # ── Iteration ────────────────────────────────────────────────
    commit_frequency_per_week: float = 0.0
    avg_change_size: float = 0.0
    active_days_ratio: float = 0.0

    # ── Refactoring ──────────────────────────────────────────────
    rename_move_ratio: float = 0.0
    complexity_reduction_trend: float = 0.0

    # ── Debugging ────────────────────────────────────────────────
    fix_revert_ratio: float = 0.0

    # ── Tooling ──────────────────────────────────────────────────
    tooling_score: float = 0.0
    dependency_management: bool = False

    # ── Data/ML ──────────────────────────────────────────────────
    ml_workflow_score: float = 0.0

    # ── Project ──────────────────────────────────────────────────
    project_complexity_score: float = 0.0

    # ── Metadata ─────────────────────────────────────────────────
    schema_version: int = FEATURE_SCHEMA_VERSION
    total_files: int = 0
    total_commits: int = 0
    total_loc: int = 0
    primary_language: str = ""
    languages_count: int = 0

    def to_dict(self) -> Dict[str, float]:
        """Convert to flat dict for storage and ML."""
        return {
            "avg_cyclomatic_complexity": self.avg_cyclomatic_complexity,
            "avg_function_length": self.avg_function_length,
            "duplication_proxy": self.duplication_proxy,
            "maintainability_index": self.maintainability_index,
            "module_count": float(self.module_count),
            "dependency_fan_out": self.dependency_fan_out,
            "layering_score": self.layering_score,
            "test_file_ratio": self.test_file_ratio,
            "test_commit_ratio": self.test_commit_ratio,
            "ci_present": 1.0 if self.ci_present else 0.0,
            "readme_density": self.readme_density,
            "docstring_ratio": self.docstring_ratio,
            "comment_ratio": self.comment_ratio,
            "commit_frequency_per_week": self.commit_frequency_per_week,
            "avg_change_size": self.avg_change_size,
            "active_days_ratio": self.active_days_ratio,
            "rename_move_ratio": self.rename_move_ratio,
            "complexity_reduction_trend": self.complexity_reduction_trend,
            "fix_revert_ratio": self.fix_revert_ratio,
            "tooling_score": self.tooling_score,
            "dependency_management": 1.0 if self.dependency_management else 0.0,
            "ml_workflow_score": self.ml_workflow_score,
            "project_complexity_score": self.project_complexity_score,
        }


# ── ML/Data file detection ───────────────────────────────────────

ML_EXTENSIONS = {".ipynb", ".pkl", ".h5", ".hdf5", ".onnx", ".pt", ".pth", ".pb"}
ML_DIR_PATTERNS = {"model", "models", "ml", "ai", "train", "eval", "pipeline"}
ML_FILE_PATTERNS = [
    "train", "eval", "predict", "model", "pipeline",
    "dataset", "feature", "preprocess", "transform",
]


def _detect_ml_workflow(
    file_paths: List[str],
    file_contents: Dict[str, str],
) -> float:
    """Score ML workflow maturity on 0-1 scale."""
    signals = 0
    max_signals = 6

    # Check for notebooks
    has_notebooks = any(p.endswith(".ipynb") for p in file_paths)
    if has_notebooks:
        signals += 1

    # Check for model files
    has_model_files = any(
        "." + p.rsplit(".", 1)[-1] in ML_EXTENSIONS
        for p in file_paths if "." in p
    )
    if has_model_files:
        signals += 1

    # Check for ML directories
    dirs = set()
    for p in file_paths:
        parts = p.replace("\\", "/").split("/")
        dirs.update(part.lower() for part in parts[:-1])

    has_ml_dirs = bool(ML_DIR_PATTERNS & dirs)
    if has_ml_dirs:
        signals += 1

    # Check for ML-related filenames
    basenames = [
        p.rsplit("/", 1)[-1].lower() if "/" in p else p.lower()
        for p in file_paths
    ]
    has_ml_files = any(
        any(pat in basename for pat in ML_FILE_PATTERNS)
        for basename in basenames
    )
    if has_ml_files:
        signals += 1

    # Check for ML imports in Python files
    ml_imports = {
        "sklearn", "tensorflow", "torch", "keras", "xgboost",
        "lightgbm", "catboost", "pandas", "numpy", "scipy",
        "transformers", "huggingface", "mlflow", "wandb",
        "optuna", "hyperopt",
    }
    for content in file_contents.values():
        if not content:
            continue
        for imp in ml_imports:
            if f"import {imp}" in content or f"from {imp}" in content:
                signals += 1
                break
        if signals >= max_signals:
            break

    # Check for eval/metrics scripts
    eval_keywords = {"accuracy", "precision", "recall", "f1", "auc", "confusion_matrix"}
    for content in file_contents.values():
        if content and any(kw in content.lower() for kw in eval_keywords):
            signals += 1
            break

    return min(signals / max_signals, 1.0)


def _calculate_tooling_score(tools: Dict[str, bool]) -> float:
    """Calculate tooling maturity score on 0-1 scale."""
    weights = {
        "docker": 0.15,
        "ci_cd": 0.20,
        "linting": 0.12,
        "formatting": 0.08,
        "type_checking": 0.10,
        "test_config": 0.10,
        "coverage": 0.08,
        "dependency_mgmt": 0.07,
        "project_config": 0.05,
        "build_automation": 0.05,
    }

    score = sum(
        weight for tool, weight in weights.items()
        if tools.get(tool, False)
    )
    return min(score, 1.0)


def _calculate_project_complexity(
    total_files: int,
    total_loc: int,
    languages_count: int,
    module_count: int,
) -> float:
    """Score project complexity on 0-1 scale.

    Based on file count, LOC, languages used, and module structure.
    """
    # File score (0-1): 50+ files is high complexity
    file_score = min(total_files / 50, 1.0)

    # LOC score (0-1): 5000+ LOC is high complexity
    loc_score = min(total_loc / 5000, 1.0)

    # Language score (0-1): 3+ languages is high complexity
    lang_score = min(languages_count / 3, 1.0)

    # Module score (0-1): 5+ top-level modules is high complexity
    mod_score = min(module_count / 5, 1.0)

    return (file_score * 0.25 + loc_score * 0.35 +
            lang_score * 0.15 + mod_score * 0.25)


def generate_repo_features(
    file_paths: List[str],
    file_contents: Dict[str, str],
    commits: List[CommitData],
    target_author: str | None = None,
) -> RepoFeatureVector:
    """Generate the complete feature vector for a repository.

    This is the main entry point for repo-level feature engineering.

    Args:
        file_paths: All file paths in the repository
        file_contents: Mapping of path → source content (for analyzable files)
        commits: List of commit data
        target_author: GitHub username to filter commits by

    Returns:
        RepoFeatureVector with all 23+ calculated features
    """
    features = RepoFeatureVector()
    features.total_files = len(file_paths)
    features.total_commits = len(commits)

    # ── Step 1: AST analysis per file ────────────────────────────
    all_file_metrics: List[FileMetrics] = []
    language_map: Dict[str, str] = {}
    python_files = 0
    test_files = 0
    total_loc = 0
    content_hashes: List[str] = []

    for path in file_paths:
        content = file_contents.get(path)

        if path.endswith(".py") and content:
            metrics = extract_python_metrics(content, path)
            python_files += 1
        elif content:
            metrics = extract_basic_metrics(content, path)
        else:
            metrics = FileMetrics()
            metrics.is_test_file = is_test_file(path)

        all_file_metrics.append(metrics)
        total_loc += metrics.loc

        if metrics.is_test_file:
            test_files += 1

        # Track language
        from app.github.normalizer import detect_language
        lang = detect_language(path)
        if lang:
            language_map[path] = lang

        # Track content hashes for duplication proxy
        if content:
            import hashlib
            h = hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()
            content_hashes.append(h)

    features.total_loc = total_loc

    # ── Code Quality features ────────────────────────────────────
    python_metrics = [
        m for m in all_file_metrics
        if m.parse_success and m.function_count > 0
    ]

    if python_metrics:
        complexities = [m.cyclomatic_complexity for m in python_metrics if m.cyclomatic_complexity > 0]
        if complexities:
            features.avg_cyclomatic_complexity = sum(complexities) / len(complexities)

        func_lengths = [m.avg_function_length for m in python_metrics if m.avg_function_length > 0]
        if func_lengths:
            features.avg_function_length = sum(func_lengths) / len(func_lengths)

        mi_scores = [m.maintainability_index for m in python_metrics if m.maintainability_index > 0]
        if mi_scores:
            features.maintainability_index = sum(mi_scores) / len(mi_scores)

    # Duplication proxy: ratio of duplicate content hashes
    if content_hashes:
        from collections import Counter
        hash_counts = Counter(content_hashes)
        duplicates = sum(1 for count in hash_counts.values() if count > 1)
        features.duplication_proxy = duplicates / len(content_hashes)

    # ── Testing features ─────────────────────────────────────────
    features.test_file_ratio = (
        test_files / features.total_files if features.total_files > 0 else 0.0
    )
    features.ci_present = any(is_ci_config(p) for p in file_paths)

    # ── Documentation features ───────────────────────────────────
    all_with_docstrings = [m for m in all_file_metrics if m.function_count > 0]
    if all_with_docstrings:
        features.docstring_ratio = (
            sum(m.docstring_ratio for m in all_with_docstrings) /
            len(all_with_docstrings)
        )

    all_with_comments = [m for m in all_file_metrics if m.sloc > 0]
    if all_with_comments:
        features.comment_ratio = (
            sum(m.comment_ratio for m in all_with_comments) /
            len(all_with_comments)
        )

    # ── Step 2: History analysis ─────────────────────────────────
    history = extract_history_metrics(commits, target_author)

    features.commit_frequency_per_week = history.commit_frequency_per_week
    features.avg_change_size = history.avg_change_size
    features.active_days_ratio = history.active_days_ratio
    features.test_commit_ratio = history.test_commit_ratio
    features.fix_revert_ratio = history.fix_ratio + history.revert_ratio
    features.rename_move_ratio = history.refactor_ratio

    # ── Step 3: Architecture analysis ────────────────────────────
    arch = analyze_architecture(file_paths, file_contents, language_map)

    features.module_count = arch.top_level_modules
    features.dependency_fan_out = arch.avg_dependency_fan_out
    features.layering_score = arch.layering_score
    features.readme_density = arch.readme_density
    features.primary_language = arch.primary_language
    features.languages_count = arch.language_count

    # ── Step 4: Tooling ──────────────────────────────────────────
    tools = detect_tools(file_paths)
    features.tooling_score = _calculate_tooling_score(tools)
    features.dependency_management = tools.get("dependency_mgmt", False)
    features.ci_present = features.ci_present or tools.get("ci_cd", False)

    # ── Step 5: ML/Data workflow ─────────────────────────────────
    features.ml_workflow_score = _detect_ml_workflow(file_paths, file_contents)

    # ── Step 6: Project complexity ───────────────────────────────
    features.project_complexity_score = _calculate_project_complexity(
        features.total_files,
        features.total_loc,
        features.languages_count,
        features.module_count,
    )

    logger.info(
        "repo_features_generated",
        files=features.total_files,
        commits=features.total_commits,
        loc=features.total_loc,
        language=features.primary_language,
    )

    return features
