"""Tests for profile generation and feature aggregation."""

from __future__ import annotations

from datetime import datetime, timezone

from app.analysis.history import CommitData
from app.analysis.profile import (
    DeveloperFingerprint,
    generate_developer_fingerprint,
)
from app.analysis.repo_features import RepoFeatureVector, generate_repo_features


# ── Repo feature generation ──────────────────────────────────────

class TestGenerateRepoFeatures:
    def test_basic_python_repo(self):
        file_paths = [
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "requirements.txt",
            "README.md",
        ]
        file_contents = {
            "src/main.py": '''
def hello(name):
    """Say hello."""
    print(f"Hello, {name}")

def add(a, b):
    return a + b
''',
            "src/utils.py": '''
import os
import sys

def get_path():
    return os.getcwd()
''',
            "tests/test_main.py": '''
def test_add():
    assert add(1, 2) == 3
''',
            "README.md": "# My Project\n\nA great project with lots of features and documentation.",
        }
        commits = [
            CommitData(sha="1", timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                       message="feat: initial commit", additions=100, deletions=0,
                       files_changed=3, author_login="user"),
            CommitData(sha="2", timestamp=datetime(2024, 1, 5, tzinfo=timezone.utc),
                       message="test: add tests", additions=20, deletions=0,
                       files_changed=1, author_login="user"),
            CommitData(sha="3", timestamp=datetime(2024, 1, 10, tzinfo=timezone.utc),
                       message="fix: resolve issue", additions=5, deletions=3,
                       files_changed=1, author_login="user"),
        ]

        features = generate_repo_features(file_paths, file_contents, commits, "user")

        assert features.total_files == 5
        assert features.total_commits == 3
        assert features.test_file_ratio > 0  # 1 test file / 5 total
        assert features.total_loc > 0
        assert features.fix_revert_ratio > 0  # 1 fix / 3 commits

    def test_empty_repo(self):
        features = generate_repo_features([], {}, [])
        assert features.total_files == 0
        assert features.total_commits == 0

    def test_feature_dict(self):
        fv = RepoFeatureVector()
        d = fv.to_dict()
        assert "avg_cyclomatic_complexity" in d
        assert "test_file_ratio" in d
        assert "tooling_score" in d
        assert len(d) == 23  # All 23 features


# ── Developer fingerprint generation ─────────────────────────────

class TestGenerateDeveloperFingerprint:
    def test_single_repo(self):
        repo_fv = RepoFeatureVector(
            avg_cyclomatic_complexity=3.0,
            maintainability_index=65.0,
            test_file_ratio=0.2,
            ci_present=True,
            docstring_ratio=0.5,
            commit_frequency_per_week=5.0,
            active_days_ratio=0.4,
            tooling_score=0.6,
            total_files=20,
            total_commits=50,
            total_loc=2000,
        )

        fingerprint = generate_developer_fingerprint([repo_fv])

        assert fingerprint.repos_analyzed == 1
        assert fingerprint.confidence > 0
        assert 0 <= fingerprint.code_quality <= 100
        assert 0 <= fingerprint.testing <= 100
        assert 0 <= fingerprint.tooling <= 100
        assert fingerprint.overall_score > 0

    def test_multiple_repos(self):
        repos = [
            RepoFeatureVector(
                maintainability_index=80.0,
                test_file_ratio=0.3,
                ci_present=True,
                total_files=30,
                total_commits=80,
                total_loc=3000,
            ),
            RepoFeatureVector(
                maintainability_index=50.0,
                test_file_ratio=0.05,
                ci_present=False,
                total_files=5,
                total_commits=10,
                total_loc=500,
            ),
        ]

        fingerprint = generate_developer_fingerprint(repos)

        assert fingerprint.repos_analyzed == 2
        # The larger repo should dominate due to higher weight
        assert fingerprint.total_commits == 90
        assert fingerprint.total_files == 35

    def test_empty_repos(self):
        fingerprint = generate_developer_fingerprint([])
        assert fingerprint.repos_analyzed == 0
        assert fingerprint.confidence == 0

    def test_confidence_scaling(self):
        # Small data = low confidence
        small = generate_developer_fingerprint([
            RepoFeatureVector(total_files=3, total_commits=5, total_loc=100),
        ])

        # More data = higher confidence
        large = generate_developer_fingerprint([
            RepoFeatureVector(total_files=50, total_commits=200, total_loc=10000),
            RepoFeatureVector(total_files=30, total_commits=100, total_loc=5000),
            RepoFeatureVector(total_files=20, total_commits=80, total_loc=3000),
        ])

        assert large.confidence > small.confidence

    def test_ml_vector(self):
        fingerprint = DeveloperFingerprint(
            code_quality=70, testing=50, architecture=60,
            documentation=40, iteration=80, debugging=30,
            tooling=65, ml_workflow=20, project_complexity=55,
        )
        vec = fingerprint.to_ml_vector()
        assert len(vec) == 9
        assert vec[0] == 70  # code_quality
        assert vec[1] == 50  # testing

    def test_feature_vector_dict(self):
        fingerprint = DeveloperFingerprint(
            code_quality=70, testing=50, architecture=60,
        )
        d = fingerprint.to_feature_vector_dict()
        assert "code_quality" in d
        assert "testing" in d
        assert d["code_quality"] == 70
