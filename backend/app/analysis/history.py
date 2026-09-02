"""Commit history and temporal feature extraction.

Analyzes commit patterns to extract:
- Commit cadence (frequency, regularity)
- Code churn (additions, deletions, change size)
- Fix/revert/refactor proxies from commit messages
- Active development days and velocity
- Temporal trends (increasing/decreasing activity)
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.logging_config import get_logger

logger = get_logger(__name__)


# ── Commit classification patterns ───────────────────────────────

FIX_PATTERNS = [
    re.compile(r"\bfix(?:e[ds])?\b", re.IGNORECASE),
    re.compile(r"\bbug(?:fix)?\b", re.IGNORECASE),
    re.compile(r"\bpatch\b", re.IGNORECASE),
    re.compile(r"\bhotfix\b", re.IGNORECASE),
    re.compile(r"\bresolve[ds]?\b", re.IGNORECASE),
    re.compile(r"\bclos(?:e[ds]?)\b", re.IGNORECASE),
]

REFACTOR_PATTERNS = [
    re.compile(r"\brefactor", re.IGNORECASE),
    re.compile(r"\bcleanup\b", re.IGNORECASE),
    re.compile(r"\bclean[\s-]?up\b", re.IGNORECASE),
    re.compile(r"\breorganize\b", re.IGNORECASE),
    re.compile(r"\brestructure\b", re.IGNORECASE),
    re.compile(r"\bsimplif", re.IGNORECASE),
    re.compile(r"\bextract\b", re.IGNORECASE),
    re.compile(r"\brename\b", re.IGNORECASE),
]

TEST_PATTERNS = [
    re.compile(r"\btest", re.IGNORECASE),
    re.compile(r"\bspec\b", re.IGNORECASE),
    re.compile(r"\bcoverage\b", re.IGNORECASE),
]

FEATURE_PATTERNS = [
    re.compile(r"\bfeat(?:ure)?[:\s]", re.IGNORECASE),
    re.compile(r"\badd(?:ed|s|ing)?\b", re.IGNORECASE),
    re.compile(r"\bimplement", re.IGNORECASE),
    re.compile(r"\bnew\b", re.IGNORECASE),
    re.compile(r"\bcreate[ds]?\b", re.IGNORECASE),
]

DOC_PATTERNS = [
    re.compile(r"\bdoc(?:s|umentation)?\b", re.IGNORECASE),
    re.compile(r"\breadme\b", re.IGNORECASE),
    re.compile(r"\bcomment", re.IGNORECASE),
    re.compile(r"\bchangelog\b", re.IGNORECASE),
]

DEVOPS_PATTERNS = [
    re.compile(r"\bci\b", re.IGNORECASE),
    re.compile(r"\bcd\b", re.IGNORECASE),
    re.compile(r"\bdocker", re.IGNORECASE),
    re.compile(r"\bdeploy", re.IGNORECASE),
    re.compile(r"\bbuild\b", re.IGNORECASE),
    re.compile(r"\bpipeline\b", re.IGNORECASE),
    re.compile(r"\binfra", re.IGNORECASE),
]

REVERT_PATTERNS = [
    re.compile(r"\brevert", re.IGNORECASE),
    re.compile(r"\bundo\b", re.IGNORECASE),
    re.compile(r"\brollback\b", re.IGNORECASE),
]


def classify_commit(message: str) -> str:
    """Classify a commit message into a category."""
    if not message:
        return "other"

    # Order matters — more specific first
    for pattern in REVERT_PATTERNS:
        if pattern.search(message):
            return "revert"

    for pattern in FIX_PATTERNS:
        if pattern.search(message):
            return "fix"

    for pattern in REFACTOR_PATTERNS:
        if pattern.search(message):
            return "refactor"

    for pattern in TEST_PATTERNS:
        if pattern.search(message):
            return "test"

    for pattern in DOC_PATTERNS:
        if pattern.search(message):
            return "documentation"

    for pattern in DEVOPS_PATTERNS:
        if pattern.search(message):
            return "devops"

    for pattern in FEATURE_PATTERNS:
        if pattern.search(message):
            return "feature"

    return "other"


# ── Data structures ──────────────────────────────────────────────

@dataclass
class CommitData:
    """Normalized commit data for analysis."""
    sha: str
    timestamp: datetime
    message: str
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    author_login: str = ""
    category: str = ""


@dataclass
class HistoryMetrics:
    """Complete temporal metrics for a repository."""

    # Commit cadence
    total_commits: int = 0
    commit_frequency_per_week: float = 0.0
    avg_commits_per_active_day: float = 0.0
    active_days: int = 0
    total_days: int = 0
    active_days_ratio: float = 0.0

    # Time span
    first_commit_date: Optional[datetime] = None
    last_commit_date: Optional[datetime] = None
    project_age_days: int = 0

    # Code churn
    total_additions: int = 0
    total_deletions: int = 0
    total_churn: int = 0
    avg_change_size: float = 0.0
    median_change_size: float = 0.0
    avg_files_per_commit: float = 0.0

    # Commit classification ratios
    fix_ratio: float = 0.0
    refactor_ratio: float = 0.0
    test_commit_ratio: float = 0.0
    feature_ratio: float = 0.0
    doc_ratio: float = 0.0
    devops_ratio: float = 0.0
    revert_ratio: float = 0.0

    # Classification counts
    commit_categories: Dict[str, int] = field(default_factory=dict)

    # Activity patterns
    day_of_week_distribution: Dict[str, int] = field(default_factory=dict)
    hour_distribution: Dict[int, int] = field(default_factory=dict)

    # Trends (slope of activity over time, positive = increasing)
    activity_trend: float = 0.0
    change_size_trend: float = 0.0

    # Burst detection
    max_commits_in_day: int = 0
    coding_streak_days: int = 0


def extract_history_metrics(
    commits: List[CommitData],
    target_author: str | None = None,
) -> HistoryMetrics:
    """Extract temporal features from commit history.

    Args:
        commits: List of commit data, ideally sorted by timestamp.
        target_author: If provided, only analyze commits by this author.

    Returns:
        HistoryMetrics with all calculated temporal features.
    """
    metrics = HistoryMetrics()

    if not commits:
        return metrics

    # Filter to target author if specified
    if target_author:
        commits = [
            c for c in commits
            if c.author_login and c.author_login.lower() == target_author.lower()
        ]

    if not commits:
        return metrics

    # Sort by timestamp
    commits = sorted(commits, key=lambda c: c.timestamp)

    # Classify commits
    for commit in commits:
        commit.category = classify_commit(commit.message)

    metrics.total_commits = len(commits)

    # ── Time span ────────────────────────────────────────────────
    metrics.first_commit_date = commits[0].timestamp
    metrics.last_commit_date = commits[-1].timestamp
    metrics.project_age_days = max(
        1,
        (metrics.last_commit_date - metrics.first_commit_date).days
    )

    # ── Commit cadence ───────────────────────────────────────────
    weeks = max(1, metrics.project_age_days / 7)
    metrics.commit_frequency_per_week = metrics.total_commits / weeks

    # Active days (unique dates with commits)
    active_dates = set()
    for c in commits:
        active_dates.add(c.timestamp.date())

    metrics.active_days = len(active_dates)
    metrics.total_days = metrics.project_age_days
    metrics.active_days_ratio = (
        metrics.active_days / metrics.total_days
        if metrics.total_days > 0 else 0.0
    )
    metrics.avg_commits_per_active_day = (
        metrics.total_commits / metrics.active_days
        if metrics.active_days > 0 else 0.0
    )

    # ── Code churn ───────────────────────────────────────────────
    change_sizes = []
    for c in commits:
        metrics.total_additions += c.additions
        metrics.total_deletions += c.deletions
        change_size = c.additions + c.deletions
        change_sizes.append(change_size)

    metrics.total_churn = metrics.total_additions + metrics.total_deletions
    metrics.avg_change_size = (
        sum(change_sizes) / len(change_sizes) if change_sizes else 0.0
    )

    # Median change size
    if change_sizes:
        sorted_sizes = sorted(change_sizes)
        mid = len(sorted_sizes) // 2
        metrics.median_change_size = (
            sorted_sizes[mid] if len(sorted_sizes) % 2
            else (sorted_sizes[mid - 1] + sorted_sizes[mid]) / 2
        )

    files_per_commit = [c.files_changed for c in commits]
    metrics.avg_files_per_commit = (
        sum(files_per_commit) / len(files_per_commit)
        if files_per_commit else 0.0
    )

    # ── Commit classification ratios ─────────────────────────────
    categories = Counter(c.category for c in commits)
    metrics.commit_categories = dict(categories)

    n = metrics.total_commits
    metrics.fix_ratio = categories.get("fix", 0) / n
    metrics.refactor_ratio = categories.get("refactor", 0) / n
    metrics.test_commit_ratio = categories.get("test", 0) / n
    metrics.feature_ratio = categories.get("feature", 0) / n
    metrics.doc_ratio = categories.get("documentation", 0) / n
    metrics.devops_ratio = categories.get("devops", 0) / n
    metrics.revert_ratio = categories.get("revert", 0) / n

    # ── Activity patterns ────────────────────────────────────────
    day_names = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]
    day_counts: Dict[str, int] = defaultdict(int)
    hour_counts: Dict[int, int] = defaultdict(int)

    for c in commits:
        day_counts[day_names[c.timestamp.weekday()]] += 1
        hour_counts[c.timestamp.hour] += 1

    metrics.day_of_week_distribution = dict(day_counts)
    metrics.hour_distribution = dict(hour_counts)

    # ── Burst and streak detection ───────────────────────────────
    date_commit_counts: Dict = Counter(c.timestamp.date() for c in commits)
    metrics.max_commits_in_day = max(date_commit_counts.values()) if date_commit_counts else 0

    # Longest streak of consecutive days with commits
    if active_dates:
        sorted_dates = sorted(active_dates)
        current_streak = 1
        max_streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        metrics.coding_streak_days = max_streak

    # ── Trends ───────────────────────────────────────────────────
    # Simple linear trend: divide history into halves, compare rates
    if metrics.total_commits >= 4:
        mid_idx = len(commits) // 2
        first_half = commits[:mid_idx]
        second_half = commits[mid_idx:]

        first_span = max(1, (first_half[-1].timestamp - first_half[0].timestamp).days)
        second_span = max(1, (second_half[-1].timestamp - second_half[0].timestamp).days)

        first_rate = len(first_half) / first_span
        second_rate = len(second_half) / second_span

        # Positive = accelerating, negative = decelerating
        metrics.activity_trend = (
            (second_rate - first_rate) / first_rate if first_rate > 0 else 0.0
        )

        # Change size trend
        first_avg_size = sum(
            c.additions + c.deletions for c in first_half
        ) / len(first_half)
        second_avg_size = sum(
            c.additions + c.deletions for c in second_half
        ) / len(second_half)

        metrics.change_size_trend = (
            (second_avg_size - first_avg_size) / first_avg_size
            if first_avg_size > 0 else 0.0
        )

    return metrics
