"""Tests for AST feature extraction."""

from __future__ import annotations

from app.analysis.ast_features import (
    FileMetrics,
    detect_tools,
    extract_basic_metrics,
    extract_python_metrics,
    is_ci_config,
    is_test_file,
)


# ── Test file detection ──────────────────────────────────────────

class TestIsTestFile:
    def test_test_prefix(self):
        assert is_test_file("test_main.py") is True

    def test_test_suffix(self):
        assert is_test_file("main_test.py") is True

    def test_conftest(self):
        assert is_test_file("conftest.py") is True

    def test_tests_directory(self):
        assert is_test_file("tests/test_auth.py") is True

    def test_nested_tests(self):
        assert is_test_file("src/tests/unit/test_models.py") is True

    def test_regular_file(self):
        assert is_test_file("src/main.py") is False

    def test_not_test(self):
        assert is_test_file("utils/helpers.py") is False


# ── CI/CD detection ──────────────────────────────────────────────

class TestIsCIConfig:
    def test_github_actions(self):
        assert is_ci_config(".github/workflows/ci.yml") is True

    def test_travis(self):
        assert is_ci_config(".travis.yml") is True

    def test_regular_yaml(self):
        assert is_ci_config("config.yml") is False


# ── Tooling detection ────────────────────────────────────────────

class TestDetectTools:
    def test_docker(self):
        tools = detect_tools(["Dockerfile", "docker-compose.yml", "src/main.py"])
        assert tools["docker"] is True

    def test_linting(self):
        tools = detect_tools([".flake8", "src/app.py"])
        assert tools["linting"] is True

    def test_no_tools(self):
        tools = detect_tools(["main.py", "utils.py"])
        assert tools["docker"] is False
        assert tools["linting"] is False

    def test_ci_cd_via_github_actions(self):
        tools = detect_tools([".github/workflows/test.yml", "main.py"])
        assert tools["ci_cd"] is True


# ── Python AST extraction ────────────────────────────────────────

class TestExtractPythonMetrics:
    def test_simple_function(self):
        source = '''
def hello(name):
    """Say hello."""
    print(f"Hello, {name}")
'''
        metrics = extract_python_metrics(source, "hello.py")
        assert metrics.parse_success is True
        assert metrics.function_count == 1
        assert metrics.functions_with_docstrings == 1
        assert metrics.docstring_ratio == 1.0

    def test_class_with_methods(self):
        source = '''
class Calculator:
    """A calculator."""

    def add(self, a, b):
        """Add two numbers."""
        return a + b

    def subtract(self, a, b):
        return a - b
'''
        metrics = extract_python_metrics(source, "calc.py")
        assert metrics.class_count == 1
        assert metrics.function_count == 2
        assert metrics.functions_with_docstrings == 1
        assert metrics.docstring_ratio == 0.5

    def test_imports(self):
        source = '''
import os
import sys
from pathlib import Path
from typing import List, Optional
'''
        metrics = extract_python_metrics(source, "imports.py")
        assert metrics.import_count == 4

    def test_complexity(self):
        source = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            return x
    elif x == 0:
        return 0
    else:
        return -1
'''
        metrics = extract_python_metrics(source, "complex.py")
        assert metrics.cyclomatic_complexity > 1.0
        assert metrics.max_complexity > 1

    def test_empty_source(self):
        metrics = extract_python_metrics("", "empty.py")
        assert metrics.parse_success is False

    def test_syntax_error(self):
        source = "def broken(:\n  pass"
        metrics = extract_python_metrics(source, "broken.py")
        assert metrics.parse_success is False
        assert "SyntaxError" in metrics.parse_error

    def test_test_file_detection(self):
        source = "def test_something(): pass"
        metrics = extract_python_metrics(source, "test_main.py")
        assert metrics.is_test_file is True

    def test_comment_ratio(self):
        source = '''# This is a comment
# Another comment
x = 1
y = 2
z = x + y
'''
        metrics = extract_python_metrics(source, "comments.py")
        assert metrics.comment_ratio > 0

    def test_maintainability_index(self):
        source = '''
def simple():
    return 42
'''
        metrics = extract_python_metrics(source, "simple.py")
        assert metrics.maintainability_index > 0


# ── Basic metrics for non-Python files ───────────────────────────

class TestExtractBasicMetrics:
    def test_javascript(self):
        source = '''// A comment
const x = 1;
const y = 2;

function add(a, b) {
    return a + b;
}
'''
        metrics = extract_basic_metrics(source, "app.js")
        assert metrics.loc > 0
        assert metrics.comment_lines >= 1

    def test_empty(self):
        metrics = extract_basic_metrics("", "empty.txt")
        assert metrics.parse_success is False
