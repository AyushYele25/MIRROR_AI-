"""Tests for API schemas validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import AnalyzeGitHubRequest, FeatureVector, HealthResponse


class TestAnalyzeGitHubRequest:
    """Test input validation for GitHub analysis requests."""

    def test_valid_username(self):
        req = AnalyzeGitHubRequest(github_username="octocat")
        assert req.github_username == "octocat"

    def test_username_with_hyphens(self):
        req = AnalyzeGitHubRequest(github_username="my-user-name")
        assert req.github_username == "my-user-name"

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeGitHubRequest(github_username="")

    def test_username_too_long_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeGitHubRequest(github_username="a" * 40)

    def test_invalid_characters_rejected(self):
        with pytest.raises(ValidationError):
            AnalyzeGitHubRequest(github_username="user name spaces")


class TestFeatureVector:
    """Test feature vector schema."""

    def test_defaults(self):
        fv = FeatureVector()
        assert fv.code_quality == 0.0
        assert fv.testing == 0.0
        assert fv.architecture == 0.0

    def test_custom_values(self):
        fv = FeatureVector(code_quality=85.5, testing=70.0)
        assert fv.code_quality == 85.5
        assert fv.testing == 70.0


class TestHealthResponse:
    """Test health response schema."""

    def test_defaults(self):
        health = HealthResponse()
        assert health.status == "healthy"
        assert health.version == "0.1.0"
