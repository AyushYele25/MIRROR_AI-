"""Tests for ML layer — role-fit, similarity, and clustering."""

from __future__ import annotations

from app.ml.role_fit import (
    calculate_role_fit,
    get_available_roles,
    get_role_definition,
)
from app.ml.similarity import (
    cosine_similarity,
    find_similar_profiles,
    compute_similarity_matrix,
)


# ── Role-fit ─────────────────────────────────────────────────────

class TestRoleFit:
    def test_available_roles(self):
        roles = get_available_roles()
        assert "ML Engineer" in roles
        assert "Software Engineer" in roles
        assert "Data Scientist" in roles
        assert len(roles) >= 5

    def test_role_definition(self):
        defn = get_role_definition("Software Engineer")
        assert len(defn) > 0
        assert all("dimension" in s and "target_score" in s for s in defn)

    def test_excellent_fit(self):
        """A profile that matches SWE requirements well."""
        fingerprint = {
            "code_quality": 85, "testing": 80, "architecture": 80,
            "tooling": 75, "debugging": 65, "documentation": 60,
            "iteration": 60, "ml_workflow": 20, "project_complexity": 50,
        }
        result = calculate_role_fit(fingerprint, "Software Engineer")
        assert result.overall_fit_score >= 70
        assert result.overall_fit_label in ("Excellent Fit", "Good Fit")
        assert len(result.strengths) > 0

    def test_early_stage_fit(self):
        """A profile with low scores across the board."""
        fingerprint = {
            "code_quality": 10, "testing": 5, "architecture": 10,
            "tooling": 5, "debugging": 10, "documentation": 5,
            "iteration": 15, "ml_workflow": 0, "project_complexity": 5,
        }
        result = calculate_role_fit(fingerprint, "Software Engineer")
        assert result.overall_fit_score < 30
        assert len(result.gaps) > 0
        assert len(result.top_gaps) > 0

    def test_next_challenge_generated(self):
        fingerprint = {
            "code_quality": 50, "testing": 15, "architecture": 40,
            "tooling": 20, "debugging": 30, "documentation": 25,
            "iteration": 40, "ml_workflow": 0, "project_complexity": 20,
        }
        result = calculate_role_fit(fingerprint, "Software Engineer")
        assert result.next_challenge is not None
        assert "title" in result.next_challenge
        assert "milestones" in result.next_challenge

    def test_unknown_role_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown role"):
            calculate_role_fit({}, "Alien Engineer")

    def test_ml_engineer_role(self):
        fingerprint = {
            "code_quality": 60, "testing": 50, "architecture": 40,
            "tooling": 55, "debugging": 35, "documentation": 30,
            "iteration": 45, "ml_workflow": 90, "project_complexity": 40,
        }
        result = calculate_role_fit(fingerprint, "ML Engineer")
        # Should score well on ML but have gaps elsewhere
        assert result.overall_fit_score > 30


# ── Similarity ───────────────────────────────────────────────────

class TestSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, a) > 0.99

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(cosine_similarity(a, b)) < 0.01

    def test_zero_vector(self):
        assert cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0

    def test_find_similar(self):
        query = [80.0, 60.0, 70.0, 50.0, 40.0, 30.0, 65.0, 10.0, 45.0]
        candidates = [
            [78.0, 58.0, 68.0, 48.0, 38.0, 28.0, 63.0, 8.0, 43.0],  # Very similar
            [10.0, 90.0, 10.0, 90.0, 10.0, 90.0, 10.0, 90.0, 10.0],  # Very different
            [75.0, 55.0, 65.0, 45.0, 35.0, 25.0, 60.0, 5.0, 40.0],   # Similar
        ]
        results = find_similar_profiles(
            query, candidates, ["user1", "user2", "user3"],
        )
        assert len(results) >= 1
        # Most similar should be first
        assert results[0].username in ("user1", "user3")
        assert results[0].similarity > 0.9

    def test_similarity_matrix(self):
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ]
        matrix = compute_similarity_matrix(vectors)
        assert len(matrix) == 3
        # Diagonal should be 1.0
        assert abs(matrix[0][0] - 1.0) < 0.01
        assert abs(matrix[1][1] - 1.0) < 0.01

    def test_empty_candidates(self):
        results = find_similar_profiles([1, 2, 3], [], [])
        assert results == []


# ── Validator tests ──────────────────────────────────────────────

class TestValidators:
    def test_validate_json(self):
        from app.llm.validators import validate_json_response
        assert validate_json_response('{"key": "value"}') == {"key": "value"}
        assert validate_json_response("invalid") is None
        assert validate_json_response("") is None

    def test_validate_json_with_code_fences(self):
        from app.llm.validators import validate_json_response
        raw = '```json\n{"key": "value"}\n```'
        result = validate_json_response(raw)
        assert result == {"key": "value"}

    def test_validate_explanation_clean(self):
        from app.llm.validators import validate_explanation
        assert validate_explanation(
            "The repositories show consistent test coverage above 60%.",
            [{"metric_name": "test_coverage"}],
        ) is True

    def test_validate_explanation_forbidden(self):
        from app.llm.validators import validate_explanation
        assert validate_explanation(
            "This developer is clearly very intelligent and creative.",
            [],
        ) is False

    def test_validate_explanation_fabrication(self):
        from app.llm.validators import validate_explanation
        assert validate_explanation(
            "The developer has won industry-leading awards for code quality.",
            [],
        ) is False

    def test_sanitize(self):
        from app.llm.validators import sanitize_explanation
        result = sanitize_explanation("This developer is brilliant and passionate.")
        assert "brilliant" not in result
        assert "passionate" not in result
