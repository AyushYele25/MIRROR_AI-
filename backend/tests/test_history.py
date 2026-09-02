"""Tests for commit history analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.analysis.history import (
    CommitData,
    classify_commit,
    extract_history_metrics,
)


# ── Commit classification ────────────────────────────────────────

class TestClassifyCommit:
    def test_fix(self):
        assert classify_commit("fix: resolve login bug") == "fix"

    def test_bugfix(self):
        assert classify_commit("bugfix: patch null pointer") == "fix"

    def test_refactor(self):
        assert classify_commit("refactor: simplify auth module") == "refactor"

    def test_test(self):
        assert classify_commit("add unit tests for user service") == "test"

    def test_feature(self):
        assert classify_commit("feat: add user authentication") == "feature"

    def test_documentation(self):
        assert classify_commit("update README with setup instructions") == "documentation"

    def test_devops(self):
        assert classify_commit("ci: add GitHub Actions workflow") == "devops"

    def test_revert(self):
        assert classify_commit("Revert 'add broken feature'") == "revert"

    def test_other(self):
        assert classify_commit("initial commit") == "other"

    def test_empty(self):
        assert classify_commit("") == "other"


# ── History metrics extraction ───────────────────────────────────

def _make_commits(count: int, days_apart: int = 1, base_date: datetime | None = None) -> list[CommitData]:
    """Create a list of test commits spaced evenly."""
    base = base_date or datetime(2024, 1, 1, tzinfo=timezone.utc)
    commits = []
    for i in range(count):
        commits.append(CommitData(
            sha=f"sha{i:04d}",
            timestamp=base + timedelta(days=i * days_apart),
            message=f"commit {i}",
            additions=50 + i * 10,
            deletions=10 + i * 5,
            files_changed=2 + i,
            author_login="testuser",
        ))
    return commits


class TestExtractHistoryMetrics:
    def test_empty_commits(self):
        metrics = extract_history_metrics([])
        assert metrics.total_commits == 0

    def test_basic_metrics(self):
        commits = _make_commits(10, days_apart=3)
        metrics = extract_history_metrics(commits)

        assert metrics.total_commits == 10
        assert metrics.first_commit_date is not None
        assert metrics.last_commit_date is not None
        assert metrics.project_age_days > 0

    def test_commit_frequency(self):
        # 7 commits over 7 days = ~1 per day = ~7 per week
        commits = _make_commits(7, days_apart=1)
        metrics = extract_history_metrics(commits)
        assert metrics.commit_frequency_per_week > 5

    def test_active_days_ratio(self):
        commits = _make_commits(5, days_apart=1)
        metrics = extract_history_metrics(commits)
        assert metrics.active_days == 5
        assert metrics.active_days_ratio > 0.5

    def test_code_churn(self):
        commits = _make_commits(5)
        metrics = extract_history_metrics(commits)
        assert metrics.total_additions > 0
        assert metrics.total_deletions > 0
        assert metrics.avg_change_size > 0

    def test_commit_classification_ratios(self):
        commits = [
            CommitData(sha="1", timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                       message="fix: bug", additions=10, deletions=5),
            CommitData(sha="2", timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                       message="feat: new feature", additions=100, deletions=0),
            CommitData(sha="3", timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc),
                       message="test: add tests", additions=50, deletions=0),
            CommitData(sha="4", timestamp=datetime(2024, 1, 4, tzinfo=timezone.utc),
                       message="refactor: cleanup", additions=20, deletions=30),
        ]
        metrics = extract_history_metrics(commits)

        assert metrics.fix_ratio == 0.25
        assert metrics.feature_ratio == 0.25
        assert metrics.test_commit_ratio == 0.25
        assert metrics.refactor_ratio == 0.25

    def test_author_filtering(self):
        commits = [
            CommitData(sha="1", timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                       message="my commit", author_login="me"),
            CommitData(sha="2", timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
                       message="other commit", author_login="other"),
            CommitData(sha="3", timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc),
                       message="my second", author_login="me"),
        ]
        metrics = extract_history_metrics(commits, target_author="me")
        assert metrics.total_commits == 2

    def test_streak_detection(self):
        # 5 consecutive days
        commits = _make_commits(5, days_apart=1)
        metrics = extract_history_metrics(commits)
        assert metrics.coding_streak_days == 5

    def test_activity_trend(self):
        # Create accelerating pattern: few early commits, more later
        commits = _make_commits(20, days_apart=2)
        metrics = extract_history_metrics(commits)
        # With uniform spacing, trend should be near 0
        assert isinstance(metrics.activity_trend, float)
