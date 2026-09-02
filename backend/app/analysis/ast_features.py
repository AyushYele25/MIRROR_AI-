"""Python AST feature extractor using ast + Radon.

Extracts per-file metrics:
- Cyclomatic complexity (per function, averaged)
- Function/class/import counts
- Docstring and comment ratios
- Maintainability Index
- Halstead volume
- Function length statistics
- Test file detection
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)

# ── Test file detection patterns ─────────────────────────────────

TEST_FILE_PATTERNS = [
    re.compile(r"^test_.*\.py$"),
    re.compile(r"^.*_test\.py$"),
    re.compile(r"^tests?\.py$"),
    re.compile(r"^conftest\.py$"),
]

TEST_DIR_PATTERNS = [
    "tests", "test", "testing", "spec", "specs",
]


def is_test_file(path: str) -> bool:
    """Determine if a file path looks like a test file."""
    parts = path.lower().replace("\\", "/").split("/")
    filename = parts[-1]

    # Check if any directory in the path is a test directory
    for part in parts[:-1]:
        if part in TEST_DIR_PATTERNS:
            return True

    # Check filename patterns
    for pattern in TEST_FILE_PATTERNS:
        if pattern.match(filename):
            return True

    return False


# ── CI/CD detection ──────────────────────────────────────────────

CI_CONFIG_PATHS = {
    ".github/workflows",
    ".travis.yml",
    ".circleci/config.yml",
    "Jenkinsfile",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    ".drone.yml",
    "bitbucket-pipelines.yml",
    "cloudbuild.yaml",
    "appveyor.yml",
}


def is_ci_config(path: str) -> bool:
    """Check if a file path is a CI/CD configuration."""
    normalized = path.lower().replace("\\", "/")
    for ci_path in CI_CONFIG_PATHS:
        if ci_path.lower() in normalized:
            return True
    return False


# ── Tooling detection ────────────────────────────────────────────

TOOL_CONFIGS = {
    # Containerization
    "dockerfile": "docker",
    "docker-compose.yml": "docker",
    "docker-compose.yaml": "docker",
    ".dockerignore": "docker",

    # Linting
    ".flake8": "linting",
    ".pylintrc": "linting",
    "pylintrc": "linting",
    ".eslintrc": "linting",
    ".eslintrc.json": "linting",
    ".eslintrc.js": "linting",
    ".eslintrc.yml": "linting",
    "biome.json": "linting",
    "ruff.toml": "linting",

    # Formatting
    ".prettierrc": "formatting",
    ".prettierrc.json": "formatting",
    ".prettierrc.js": "formatting",
    ".editorconfig": "formatting",
    "pyproject.toml": "project_config",

    # Type checking
    "mypy.ini": "type_checking",
    ".mypy.ini": "type_checking",
    "pyrightconfig.json": "type_checking",
    "tsconfig.json": "type_checking",

    # Testing config
    "pytest.ini": "test_config",
    "setup.cfg": "project_config",
    "tox.ini": "test_config",
    ".coveragerc": "coverage",
    "jest.config.js": "test_config",
    "jest.config.ts": "test_config",
    "vitest.config.ts": "test_config",

    # Dependency management
    "requirements.txt": "dependency_mgmt",
    "Pipfile": "dependency_mgmt",
    "Pipfile.lock": "dependency_mgmt",
    "poetry.lock": "dependency_mgmt",
    "package.json": "dependency_mgmt",
    "package-lock.json": "dependency_mgmt",
    "yarn.lock": "dependency_mgmt",
    "pnpm-lock.yaml": "dependency_mgmt",
    "go.mod": "dependency_mgmt",
    "Cargo.toml": "dependency_mgmt",
    "Gemfile": "dependency_mgmt",

    # Infrastructure
    "terraform.tf": "infrastructure",
    "main.tf": "infrastructure",
    "Makefile": "build_automation",
    "justfile": "build_automation",

    # Database
    "alembic.ini": "database_migrations",
}


def detect_tools(file_paths: List[str]) -> dict[str, bool]:
    """Detect which engineering tools are present from file paths."""
    found_categories: set[str] = set()

    for path in file_paths:
        basename = path.rsplit("/", 1)[-1].lower() if "/" in path else path.lower()
        category = TOOL_CONFIGS.get(basename)
        if category:
            found_categories.add(category)

    return {
        "docker": "docker" in found_categories,
        "ci_cd": any(is_ci_config(p) for p in file_paths),
        "linting": "linting" in found_categories,
        "formatting": "formatting" in found_categories,
        "type_checking": "type_checking" in found_categories,
        "test_config": "test_config" in found_categories,
        "coverage": "coverage" in found_categories,
        "dependency_mgmt": "dependency_mgmt" in found_categories,
        "project_config": "project_config" in found_categories,
        "database_migrations": "database_migrations" in found_categories,
        "build_automation": "build_automation" in found_categories,
        "infrastructure": "infrastructure" in found_categories,
    }


# ── AST Feature Extraction ──────────────────────────────────────

@dataclass
class FunctionInfo:
    """Information about a parsed function."""
    name: str
    lineno: int
    end_lineno: int
    length: int
    has_docstring: bool
    complexity: int = 1
    is_method: bool = False


@dataclass
class FileMetrics:
    """Complete metrics extracted from a single source file."""
    # Basic counts
    loc: int = 0
    sloc: int = 0
    blank_lines: int = 0
    comment_lines: int = 0

    # Structure
    function_count: int = 0
    class_count: int = 0
    import_count: int = 0

    # Quality
    cyclomatic_complexity: float = 0.0
    max_complexity: int = 0
    maintainability_index: float = 0.0
    halstead_volume: float = 0.0

    # Documentation
    docstring_ratio: float = 0.0
    comment_ratio: float = 0.0

    # Function statistics
    avg_function_length: float = 0.0
    max_function_length: int = 0
    functions_with_docstrings: int = 0

    # Flags
    is_test_file: bool = False
    has_main_guard: bool = False

    # Raw data for aggregation
    functions: List[FunctionInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)

    # Parse status
    parse_success: bool = True
    parse_error: str = ""


def _count_lines(source: str) -> tuple[int, int, int, int]:
    """Count LOC, SLOC, blank lines, and comment lines."""
    lines = source.split("\n")
    loc = len(lines)
    blank = 0
    comments = 0
    in_docstring = False
    docstring_char = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            blank += 1
            continue

        # Track docstrings (triple-quoted strings)
        if in_docstring:
            if docstring_char and docstring_char in stripped:
                in_docstring = False
            continue

        if stripped.startswith('"""') or stripped.startswith("'''"):
            docstring_char = stripped[:3]
            if stripped.count(docstring_char) >= 2:
                # Single-line docstring
                continue
            in_docstring = True
            continue

        if stripped.startswith("#"):
            comments += 1

    sloc = loc - blank - comments
    return loc, sloc, blank, comments


def _extract_functions(tree: ast.AST) -> List[FunctionInfo]:
    """Extract function information from AST."""
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Calculate function length
            end_line = getattr(node, "end_lineno", node.lineno)
            length = end_line - node.lineno + 1

            # Check for docstring
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
            )

            # Check if it's a method (inside a class)
            is_method = False
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for child in ast.iter_child_nodes(parent):
                        if child is node:
                            is_method = True
                            break

            functions.append(FunctionInfo(
                name=node.name,
                lineno=node.lineno,
                end_lineno=end_line,
                length=length,
                has_docstring=has_docstring,
                is_method=is_method,
            ))

    return functions


def _extract_imports(tree: ast.AST) -> List[str]:
    """Extract import names from AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)
    return imports


def _has_main_guard(tree: ast.AST) -> bool:
    """Check if the file has an if __name__ == '__main__' guard."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            try:
                test = node.test
                if isinstance(test, ast.Compare):
                    left = test.left
                    if (isinstance(left, ast.Name) and left.id == "__name__"):
                        return True
            except (AttributeError, IndexError):
                pass
    return False


def _count_classes(tree: ast.AST) -> int:
    """Count class definitions in AST."""
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))


def extract_python_metrics(source: str, file_path: str = "") -> FileMetrics:
    """Extract all metrics from Python source code.

    This is the main entry point for Python file analysis.

    Args:
        source: Python source code as string
        file_path: File path (used for test detection)

    Returns:
        FileMetrics with all calculated values
    """
    metrics = FileMetrics()
    metrics.is_test_file = is_test_file(file_path)

    if not source or not source.strip():
        metrics.parse_success = False
        metrics.parse_error = "Empty source"
        return metrics

    # Line counts
    metrics.loc, metrics.sloc, metrics.blank_lines, metrics.comment_lines = (
        _count_lines(source)
    )
    metrics.comment_ratio = (
        metrics.comment_lines / metrics.sloc if metrics.sloc > 0 else 0.0
    )

    # Parse AST
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        metrics.parse_success = False
        metrics.parse_error = f"SyntaxError: {e}"
        return metrics

    # Structure
    metrics.functions = _extract_functions(tree)
    metrics.function_count = len(metrics.functions)
    metrics.class_count = _count_classes(tree)
    metrics.imports = _extract_imports(tree)
    metrics.import_count = len(metrics.imports)
    metrics.has_main_guard = _has_main_guard(tree)

    # Docstring ratio
    if metrics.function_count > 0:
        metrics.functions_with_docstrings = sum(
            1 for f in metrics.functions if f.has_docstring
        )
        metrics.docstring_ratio = (
            metrics.functions_with_docstrings / metrics.function_count
        )

    # Function length stats
    if metrics.functions:
        lengths = [f.length for f in metrics.functions]
        metrics.avg_function_length = sum(lengths) / len(lengths)
        metrics.max_function_length = max(lengths)

    # ── Radon metrics (complexity, MI, Halstead) ─────────────────
    try:
        from radon.complexity import cc_visit
        from radon.metrics import mi_visit, h_visit

        # Cyclomatic complexity
        cc_results = cc_visit(source)
        if cc_results:
            complexities = [r.complexity for r in cc_results]
            metrics.cyclomatic_complexity = sum(complexities) / len(complexities)
            metrics.max_complexity = max(complexities)

            # Map complexity back to functions
            cc_map = {r.name: r.complexity for r in cc_results}
            for func in metrics.functions:
                if func.name in cc_map:
                    func.complexity = cc_map[func.name]

        # Maintainability Index (0-100, higher = better)
        metrics.maintainability_index = mi_visit(source, multi=True)

        # Halstead volume
        h_results = h_visit(source)
        if h_results and hasattr(h_results, "total"):
            total = h_results.total
            if hasattr(total, "volume") and total.volume:
                metrics.halstead_volume = total.volume

    except Exception as e:
        logger.debug("radon_analysis_failed", path=file_path, error=str(e))

    return metrics


# ── Non-Python file basic metrics ────────────────────────────────

def extract_basic_metrics(source: str, file_path: str = "") -> FileMetrics:
    """Extract basic line-count metrics for non-Python files.

    For files we can't AST-parse, we still count lines, comments,
    and detect test patterns.
    """
    metrics = FileMetrics()
    metrics.is_test_file = is_test_file(file_path)

    if not source or not source.strip():
        metrics.parse_success = False
        return metrics

    lines = source.split("\n")
    metrics.loc = len(lines)
    metrics.blank_lines = sum(1 for l in lines if not l.strip())
    metrics.sloc = metrics.loc - metrics.blank_lines

    # Rough comment detection for common languages
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    comment_prefixes = {
        "js": "//", "ts": "//", "tsx": "//", "jsx": "//",
        "java": "//", "go": "//", "rs": "//", "c": "//",
        "cpp": "//", "cs": "//", "swift": "//", "kt": "//",
        "rb": "#", "sh": "#", "bash": "#", "yaml": "#",
        "yml": "#", "toml": "#", "r": "#",
    }

    prefix = comment_prefixes.get(ext, "#")
    metrics.comment_lines = sum(
        1 for l in lines if l.strip().startswith(prefix)
    )
    metrics.comment_ratio = (
        metrics.comment_lines / metrics.sloc if metrics.sloc > 0 else 0.0
    )

    return metrics
