"""Architecture analysis — module structure, dependencies, and layering.

Analyzes the file tree and imports to detect:
- Module/package structure and depth
- Dependency fan-out (imports per file)
- Layering patterns (routes/models/services separation)
- Project structure maturity signals
"""

from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from app.logging_config import get_logger

logger = get_logger(__name__)


# ── Architecture layer patterns ──────────────────────────────────

LAYER_PATTERNS = {
    "api_routes": re.compile(
        r"(routes?|endpoints?|views?|controllers?|handlers?|api)",
        re.IGNORECASE,
    ),
    "models_schemas": re.compile(
        r"(models?|schemas?|entities|types?|dto)",
        re.IGNORECASE,
    ),
    "services_logic": re.compile(
        r"(services?|logic|use_?cases?|interactors?|managers?)",
        re.IGNORECASE,
    ),
    "data_access": re.compile(
        r"(repositories|repos?|dao|data_?access|queries|crud|db|database)",
        re.IGNORECASE,
    ),
    "utils_helpers": re.compile(
        r"(utils?|helpers?|common|shared|lib|tools?)",
        re.IGNORECASE,
    ),
    "config": re.compile(
        r"(config|settings?|constants?|env)",
        re.IGNORECASE,
    ),
    "tests": re.compile(
        r"(tests?|specs?|testing|__tests__)",
        re.IGNORECASE,
    ),
    "middleware": re.compile(
        r"(middleware|interceptors?|guards?|filters?|pipes?)",
        re.IGNORECASE,
    ),
    "workers": re.compile(
        r"(workers?|tasks?|jobs?|queue|celery|background)",
        re.IGNORECASE,
    ),
    "migrations": re.compile(
        r"(migrations?|alembic|flyway|seeds?)",
        re.IGNORECASE,
    ),
}


@dataclass
class ArchitectureMetrics:
    """Architecture and structure metrics for a repository."""

    # Module structure
    total_files: int = 0
    total_directories: int = 0
    top_level_modules: int = 0
    max_directory_depth: int = 0
    avg_directory_depth: float = 0.0

    # File distribution
    files_per_directory_avg: float = 0.0
    files_per_directory_max: int = 0
    largest_directory: str = ""

    # Languages
    language_distribution: Dict[str, int] = field(default_factory=dict)
    primary_language: str = ""
    language_count: int = 0

    # Layering (architecture decomposition)
    detected_layers: List[str] = field(default_factory=list)
    layering_score: float = 0.0  # 0-1, higher = better separation

    # Dependencies (from Python imports)
    avg_dependency_fan_out: float = 0.0
    max_dependency_fan_out: int = 0
    internal_imports: int = 0
    external_imports: int = 0

    # Project structure signals
    has_readme: bool = False
    has_license: bool = False
    has_setup_file: bool = False
    has_requirements: bool = False
    has_gitignore: bool = False
    has_src_layout: bool = False

    # README analysis
    readme_word_count: int = 0
    readme_density: float = 0.0  # words per file in project


def _get_directory_depth(path: str) -> int:
    """Calculate depth of a file path."""
    normalized = path.replace("\\", "/")
    return len(normalized.split("/")) - 1


def _detect_layers(directories: Set[str]) -> List[str]:
    """Detect architectural layers from directory names."""
    detected = []
    for layer_name, pattern in LAYER_PATTERNS.items():
        for dir_name in directories:
            basename = dir_name.rsplit("/", 1)[-1] if "/" in dir_name else dir_name
            if pattern.search(basename):
                detected.append(layer_name)
                break
    return detected


def _calculate_layering_score(detected_layers: List[str]) -> float:
    """Score architectural layering on 0-1 scale.

    Higher score = more distinct separation of concerns.
    """
    # Key layers that indicate good architecture
    key_layers = {
        "api_routes", "models_schemas", "services_logic",
        "data_access", "config", "tests",
    }

    found_key = sum(1 for l in detected_layers if l in key_layers)
    total_found = len(detected_layers)

    # Score based on how many key layers are present
    # Having 3+ key layers out of 6 is good separation
    key_score = min(found_key / 3.0, 1.0)

    # Bonus for total layer count
    total_bonus = min(total_found / 5.0, 1.0) * 0.3

    return round(min(key_score + total_bonus, 1.0), 3)


def analyze_architecture(
    file_paths: List[str],
    file_contents: Dict[str, str] | None = None,
    language_map: Dict[str, str] | None = None,
) -> ArchitectureMetrics:
    """Analyze repository architecture from file paths and contents.

    Args:
        file_paths: All file paths in the repository
        file_contents: Optional mapping of path → content for deeper analysis
        language_map: Optional mapping of path → detected language

    Returns:
        ArchitectureMetrics with structure analysis
    """
    metrics = ArchitectureMetrics()
    file_contents = file_contents or {}
    language_map = language_map or {}

    if not file_paths:
        return metrics

    metrics.total_files = len(file_paths)

    # ── Directory structure ──────────────────────────────────────
    directories: Set[str] = set()
    top_level: Set[str] = set()
    dir_file_counts: Dict[str, int] = defaultdict(int)
    depths: List[int] = []

    for path in file_paths:
        normalized = path.replace("\\", "/")
        parts = normalized.split("/")

        # Track depths
        depth = len(parts) - 1
        depths.append(depth)

        # Track directories
        if len(parts) > 1:
            top_level.add(parts[0])
            parent = "/".join(parts[:-1])
            directories.add(parent)
            dir_file_counts[parent] += 1

            # Add all parent dirs
            for i in range(1, len(parts) - 1):
                directories.add("/".join(parts[:i + 1]))

    metrics.total_directories = len(directories)
    metrics.top_level_modules = len(top_level)

    if depths:
        metrics.max_directory_depth = max(depths)
        metrics.avg_directory_depth = sum(depths) / len(depths)

    if dir_file_counts:
        counts = list(dir_file_counts.values())
        metrics.files_per_directory_avg = sum(counts) / len(counts)
        metrics.files_per_directory_max = max(counts)
        metrics.largest_directory = max(dir_file_counts, key=dir_file_counts.get)

    # ── Language distribution ────────────────────────────────────
    lang_counts: Dict[str, int] = Counter()
    for path in file_paths:
        lang = language_map.get(path)
        if lang:
            lang_counts[lang] += 1

    metrics.language_distribution = dict(lang_counts)
    metrics.language_count = len(lang_counts)
    if lang_counts:
        metrics.primary_language = lang_counts.most_common(1)[0][0]

    # ── Layering ─────────────────────────────────────────────────
    metrics.detected_layers = _detect_layers(directories | top_level)
    metrics.layering_score = _calculate_layering_score(metrics.detected_layers)

    # ── Dependency analysis (Python imports) ─────────────────────
    fan_outs: List[int] = []

    for path, content in file_contents.items():
        if not path.endswith(".py") or not content:
            continue

        imports = _extract_import_names(content)
        fan_outs.append(len(imports))

        for imp in imports:
            # Heuristic: if import starts with a top-level dir name, it's internal
            first_part = imp.split(".")[0]
            if first_part in top_level:
                metrics.internal_imports += 1
            else:
                metrics.external_imports += 1

    if fan_outs:
        metrics.avg_dependency_fan_out = sum(fan_outs) / len(fan_outs)
        metrics.max_dependency_fan_out = max(fan_outs)

    # ── Project structure signals ────────────────────────────────
    lower_paths = {p.lower().replace("\\", "/") for p in file_paths}
    basenames = {p.rsplit("/", 1)[-1] if "/" in p else p for p in lower_paths}

    metrics.has_readme = any(b.startswith("readme") for b in basenames)
    metrics.has_license = any(
        b.startswith("license") or b.startswith("licence") for b in basenames
    )
    metrics.has_setup_file = bool(
        {"setup.py", "setup.cfg", "pyproject.toml"} & basenames
    )
    metrics.has_requirements = bool(
        {"requirements.txt", "pipfile", "poetry.lock", "package.json"} & basenames
    )
    metrics.has_gitignore = ".gitignore" in basenames
    metrics.has_src_layout = any(
        p.startswith("src/") for p in lower_paths
    )

    # ── README analysis ──────────────────────────────────────────
    for path, content in file_contents.items():
        basename = path.rsplit("/", 1)[-1] if "/" in path else path
        if basename.lower().startswith("readme") and content:
            metrics.readme_word_count = len(content.split())
            break

    metrics.readme_density = (
        metrics.readme_word_count / metrics.total_files
        if metrics.total_files > 0 else 0.0
    )

    return metrics


def _extract_import_names(source: str) -> List[str]:
    """Quick import extraction without full AST parsing.

    Uses regex for speed when we don't need full AST analysis.
    """
    imports = []
    for line in source.split("\n"):
        stripped = line.strip()

        # import foo, import foo.bar
        match = re.match(r"^import\s+([\w.]+)", stripped)
        if match:
            imports.append(match.group(1))
            continue

        # from foo import bar, from foo.bar import baz
        match = re.match(r"^from\s+([\w.]+)\s+import", stripped)
        if match:
            imports.append(match.group(1))

    return imports
