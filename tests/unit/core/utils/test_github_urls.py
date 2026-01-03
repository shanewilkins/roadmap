"""Tests for GitHub URL utilities."""

import pytest

from roadmap.core.utils.github_urls import (
    get_issue_url,
    get_milestone_url,
    get_repo_url,
    parse_github_number,
)


class TestGitHubUrlGeneration:
    """Test GitHub URL generation functions."""

    def test_get_issue_url(self) -> None:
        """Test issue URL generation."""
        url = get_issue_url("owner", "repo", 123)
        assert url == "https://github.com/owner/repo/issues/123"

    def test_get_issue_url_with_string_number(self) -> None:
        """Test issue URL generation with string issue number."""
        url = get_issue_url("owner", "repo", "456")
        assert url == "https://github.com/owner/repo/issues/456"

    def test_get_milestone_url(self) -> None:
        """Test milestone URL generation."""
        url = get_milestone_url("owner", "repo", 789)
        assert url == "https://github.com/owner/repo/milestone/789"

    def test_get_milestone_url_with_string_number(self) -> None:
        """Test milestone URL generation with string milestone number."""
        url = get_milestone_url("owner", "repo", "101")
        assert url == "https://github.com/owner/repo/milestone/101"

    def test_get_repo_url(self) -> None:
        """Test repository URL generation."""
        url = get_repo_url("owner", "repo")
        assert url == "https://github.com/owner/repo"

    def test_get_repo_url_with_special_characters(self) -> None:
        """Test repository URL generation with special characters."""
        url = get_repo_url("my-org", "my-repo-name")
        assert url == "https://github.com/my-org/my-repo-name"


class TestGitHubNumberParsing:
    """Test GitHub URL number parsing."""

    def test_parse_issue_url(self) -> None:
        """Test parsing issue number from URL."""
        num = parse_github_number("https://github.com/owner/repo/issues/123")
        assert num == 123

    def test_parse_milestone_url(self) -> None:
        """Test parsing milestone number from URL."""
        num = parse_github_number("https://github.com/owner/repo/milestone/456")
        assert num == 456

    def test_parse_url_with_trailing_slash(self) -> None:
        """Test parsing URL with trailing slash."""
        num = parse_github_number("https://github.com/owner/repo/issues/789/")
        assert num == 789

    def test_parse_invalid_url(self) -> None:
        """Test parsing invalid URL."""
        num = parse_github_number("https://github.com/owner/repo")
        assert num is None

    def test_parse_url_with_non_numeric_ending(self) -> None:
        """Test parsing URL with non-numeric ending."""
        num = parse_github_number("https://github.com/owner/repo/issues/abc")
        assert num is None

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string."""
        num = parse_github_number("")
        assert num is None
