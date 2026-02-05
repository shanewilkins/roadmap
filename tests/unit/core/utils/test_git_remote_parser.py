"""Tests for git remote parser utility."""

import pytest

from roadmap.core.utils.git_remote_parser import (
    get_github_from_git_remote,
    parse_github_remote,
)


class TestParseGitHubRemote:
    """Test GitHub remote URL parsing."""

    def test_parse_ssh_format(self):
        """Test parsing SSH format: git@github.com:owner/repo.git"""
        url = "git@github.com:owner/repo.git"
        owner, repo = parse_github_remote(url)

        assert owner == "owner"
        assert repo == "repo"

    def test_parse_ssh_format_without_git_extension(self):
        """Test parsing SSH format without .git extension."""
        url = "git@github.com:myorg/myrepo"
        owner, repo = parse_github_remote(url)

        assert owner == "myorg"
        assert repo == "myrepo"

    def test_parse_https_format(self):
        """Test parsing HTTPS format: https://github.com/owner/repo.git"""
        url = "https://github.com/owner/repo.git"
        owner, repo = parse_github_remote(url)

        assert owner == "owner"
        assert repo == "repo"

    def test_parse_https_format_without_git_extension(self):
        """Test parsing HTTPS format without .git extension."""
        url = "https://github.com/owner/repo"
        owner, repo = parse_github_remote(url)

        assert owner == "owner"
        assert repo == "repo"

    def test_parse_https_with_username(self):
        """Test parsing HTTPS with username: https://user@github.com/owner/repo.git"""
        url = "https://user@github.com/owner/repo.git"
        owner, repo = parse_github_remote(url)

        assert owner == "owner"
        assert repo == "repo"

    def test_parse_special_characters_in_names(self):
        """Test parsing with special characters (hyphens, underscores)."""
        url = "git@github.com:my-org_name/my-repo_name.git"
        owner, repo = parse_github_remote(url)

        assert owner == "my-org_name"
        assert repo == "my-repo_name"

    def test_parse_non_github_url_returns_none(self):
        """Test parsing non-GitHub URL returns None."""
        url = "git@gitlab.com:owner/repo.git"
        owner, repo = parse_github_remote(url)

        assert owner is None
        assert repo is None

    def test_parse_invalid_url_returns_none(self):
        """Test parsing invalid URL returns None."""
        url = "not-a-valid-url"
        owner, repo = parse_github_remote(url)

        assert owner is None
        assert repo is None

    def test_parse_empty_string_returns_none(self):
        """Test parsing empty string returns None."""
        url = ""
        owner, repo = parse_github_remote(url)

        assert owner is None
        assert repo is None

    def test_parse_none_returns_none(self):
        """Test parsing None returns None."""
        owner, repo = parse_github_remote(None)

        assert owner is None
        assert repo is None


class TestGetGitHubFromGitRemote:
    """Test auto-detection from git remote."""

    @pytest.mark.integration
    def test_get_github_from_remote_not_a_git_repo(self, tmp_path):
        """Test returns None when not in a git repository."""
        owner, repo = get_github_from_git_remote(tmp_path)

        assert owner is None
        assert repo is None

    @pytest.mark.integration
    def test_get_github_from_remote_no_origin(self, tmp_path, monkeypatch):
        """Test returns None when no origin remote configured."""
        import subprocess

        # Mock subprocess to return non-zero exit code
        def mock_run(*args, **kwargs):
            class Result:
                returncode = 1
                stdout = ""

            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)

        owner, repo = get_github_from_git_remote(tmp_path)

        assert owner is None
        assert repo is None

    @pytest.mark.integration
    def test_get_github_from_remote_timeout(self, tmp_path, monkeypatch):
        """Test handles timeout gracefully."""
        import subprocess

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        owner, repo = get_github_from_git_remote(tmp_path)

        assert owner is None
        assert repo is None
