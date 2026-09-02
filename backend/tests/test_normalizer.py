"""Tests for GitHub normalizer."""

from __future__ import annotations

import uuid

from app.github.normalizer import (
    detect_language,
    normalize_commit,
    normalize_file,
    normalize_repository,
    normalize_user,
)


class TestDetectLanguage:
    """Test language detection from file paths."""

    def test_python(self):
        assert detect_language("src/main.py") == "Python"

    def test_javascript(self):
        assert detect_language("app/index.js") == "JavaScript"

    def test_typescript(self):
        assert detect_language("components/Button.tsx") == "TypeScript"

    def test_java(self):
        assert detect_language("Main.java") == "Java"

    def test_dockerfile(self):
        assert detect_language("Dockerfile") == "Dockerfile"

    def test_makefile(self):
        assert detect_language("Makefile") == "Makefile"

    def test_unknown(self):
        assert detect_language("data.xyz") is None

    def test_markdown(self):
        assert detect_language("README.md") == "Markdown"

    def test_sql(self):
        assert detect_language("schema.sql") == "SQL"


class TestNormalizeUser:
    """Test user normalization from API response."""

    def test_basic_user(self, sample_github_user):
        user = normalize_user(sample_github_user)
        assert user.github_login == "testuser"
        assert user.display_name == "Test User"
        assert user.public_repos == 10
        assert user.avatar_url is not None

    def test_user_without_name(self):
        raw = {
            "login": "noname",
            "name": None,
            "avatar_url": None,
            "bio": None,
            "public_repos": 0,
            "created_at": None,
        }
        user = normalize_user(raw)
        assert user.display_name == "noname"
        assert user.github_created_at is None


class TestNormalizeRepository:
    """Test repository normalization."""

    def test_basic_repo(self, sample_github_repo):
        user_id = uuid.uuid4()
        repo = normalize_repository(sample_github_repo, user_id)
        assert repo.name == "test-repo"
        assert repo.full_name == "testuser/test-repo"
        assert repo.primary_language == "Python"
        assert repo.stars == 5
        assert repo.is_fork is False
        assert repo.user_id == user_id


class TestNormalizeCommit:
    """Test commit normalization."""

    def test_basic_commit(self, sample_github_commit):
        repo_id = uuid.uuid4()
        commit = normalize_commit(sample_github_commit, repo_id)
        assert commit.sha == "abc123def456789012345678901234567890abcd"
        assert commit.author_login == "testuser"
        assert commit.message == "feat: add user authentication"
        assert commit.additions == 150
        assert commit.deletions == 30
        assert commit.files_changed == 2


class TestNormalizeFile:
    """Test file normalization."""

    def test_basic_file(self, sample_tree_item):
        repo_id = uuid.uuid4()
        file = normalize_file(sample_tree_item, repo_id)
        assert file.path == "src/main.py"
        assert file.filename == "main.py"
        assert file.language == "Python"
        assert file.size_bytes == 2048

    def test_file_with_content(self, sample_tree_item):
        repo_id = uuid.uuid4()
        file = normalize_file(sample_tree_item, repo_id, content="print('hello')")
        assert file.content_hash is not None
        assert len(file.content_hash) == 64  # SHA-256 hex digest
