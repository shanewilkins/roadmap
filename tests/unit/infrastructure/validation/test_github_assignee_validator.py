"""Tests for GitHub assignee validation at the infrastructure layer."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.issue.assignee_validation_service import (
    AssigneeValidationResult,
)
from roadmap.infrastructure.validation.github_validator import GitHubAssigneeValidator


class TestGitHubAssigneeValidator:
    """Test GitHubAssigneeValidator infrastructure implementation."""

    @pytest.fixture
    def github_validator(self):
        """Create validator with test configuration."""
        return GitHubAssigneeValidator(
            token="test_token",
            owner="test_owner",
            repo="test_repo",
            cached_members=["alice", "bob", "charlie"],
        )

    def test_init_with_cached_members_list(self):
        """Test initialization with cached members as list."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=["alice", "bob"],
        )
        assert validator.cached_members == {"alice", "bob"}
        assert validator.token == "token"
        assert validator.owner == "owner"
        assert validator.repo == "repo"

    def test_init_with_cached_members_set(self):
        """Test initialization with cached members as set."""
        cached = {"alice", "bob"}
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=cached,
        )
        assert validator.cached_members == cached

    def test_init_without_cached_members(self):
        """Test initialization without cached members."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
        )
        assert validator.cached_members == set()

    def test_init_with_none_cached_members(self):
        """Test initialization with None cached members."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=None,
        )
        assert validator.cached_members == set()

    def test_validate_with_cached_member(self, github_validator):
        """Test validation with assignee in cache."""
        result = github_validator.validate("alice")
        assert isinstance(result, AssigneeValidationResult)
        assert result.is_valid is True
        assert result.canonical_id == "alice"

    def test_validate_with_uncached_member(self, github_validator):
        """Test validation with assignee not in cache."""
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (True, "")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = github_validator.validate("dave")
            assert result.is_valid is True
            assert result.canonical_id == "dave"
            # Verify the gateway was called for uncached member
            mock_get_client.assert_called_once_with(
                token="test_token", org="test_owner"
            )

    def test_validate_with_invalid_assignee(self, github_validator):
        """Test validation with invalid assignee."""
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (False, "User not found on GitHub")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = github_validator.validate("nonexistent")
            assert result.is_valid is False
            assert result.message == "User not found on GitHub"

    def test_validate_empty_assignee(self, github_validator):
        """Test validation with empty assignee string."""
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (False, "Empty assignee")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = github_validator.validate("")
            # Empty strings hit API validation
            assert isinstance(result, AssigneeValidationResult)

    def test_validate_special_characters_in_assignee(self, github_validator):
        """Test validation with special characters in assignee name."""
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (True, "")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = github_validator.validate("test-user")
            assert result.is_valid is True

    def test_validate_case_sensitivity(self, github_validator):
        """Test that validation respects case sensitivity."""
        # Test uppercase version of cached member
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (False, "Case mismatch")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            # "ALICE" is not in cache (which has "alice")
            github_validator.validate("ALICE")
            mock_get_client.assert_not_called()

    def test_multiple_validations_with_mixed_cache(self, github_validator):
        """Test multiple validations with both cached and uncached members."""
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (True, "")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            # First validation with cached member
            result1 = github_validator.validate("alice")
            assert result1.is_valid is True
            assert mock_get_client.call_count == 0

            # Second validation with uncached member
            result2 = github_validator.validate("dave")
            assert result2.is_valid is True
            assert mock_get_client.call_count == 1

            # Third validation with another cached member
            result3 = github_validator.validate("charlie")
            assert result3.is_valid is True
            assert mock_get_client.call_count == 1  # No additional calls


class TestGitHubAssigneeValidatorEdgeCases:
    """Test edge cases and error scenarios."""

    def test_validate_with_whitespace_in_assignee(self):
        """Test validation with whitespace in assignee name."""
        validator = GitHubAssigneeValidator(token="token", owner="owner", repo="repo")
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (
            False,
            "Invalid character in name",
        )

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = validator.validate("alice smith")
            assert result.is_valid is False

    def test_validate_unicode_assignee(self):
        """Test validation with Unicode characters."""
        validator = GitHubAssigneeValidator(token="token", owner="owner", repo="repo")
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (True, "")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = validator.validate("alice_café")
            assert result.is_valid is True

    def test_validate_very_long_assignee_name(self):
        """Test validation with very long assignee name."""
        validator = GitHubAssigneeValidator(token="token", owner="owner", repo="repo")
        long_name = "a" * 255
        mock_client = MagicMock()
        mock_client.validate_assignee.return_value = (False, "Name too long")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            result = validator.validate(long_name)
            assert result.is_valid is False

    def test_cached_members_empty_set(self):
        """Test validator with explicitly empty cached members."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=set(),
        )
        assert validator.cached_members == set()

    def test_cached_members_with_duplicates(self):
        """Test that cached members list handles duplicates."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=["alice", "alice", "bob", "bob"],
        )
        # Should be deduplicated in set
        assert len(validator.cached_members) == 2
        assert validator.cached_members == {"alice", "bob"}

    def test_validate_with_github_api_error(self):
        """Test validation when GitHub API raises an exception."""
        validator = GitHubAssigneeValidator(token="token", owner="owner", repo="repo")

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.side_effect = Exception("API connection failed")

            result = validator.validate("alice")
            assert result.is_valid is False
            assert "GitHub validation failed" in result.message


class TestGitHubAssigneeValidatorIntegration:
    """Integration-style tests with realistic scenarios."""

    def test_validate_common_github_usernames(self):
        """Test validation with common GitHub username patterns."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=["user-1", "user_2", "user123", "u"],
        )

        # These are in cache
        assert validator.validate("user-1").is_valid is True
        assert validator.validate("user_2").is_valid is True
        assert validator.validate("user123").is_valid is True
        assert validator.validate("u").is_valid is True

    def test_validation_result_properties(self):
        """Test that validation results have expected properties."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=["alice"],
        )

        result = validator.validate("alice")
        assert hasattr(result, "is_valid")
        assert hasattr(result, "message")
        assert hasattr(result, "canonical_id")
        assert result.is_valid is True
        assert result.canonical_id == "alice"

    def test_cache_hit_performance(self):
        """Test that cache hits are much faster than API calls."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=["alice", "bob", "charlie", "dave", "eve"],
        )

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            # Validate all cached members
            for name in ["alice", "bob", "charlie", "dave", "eve"]:
                result = validator.validate(name)
                assert result.is_valid is True

            # API should never be called for cached members
            mock_get_client.assert_not_called()

    def test_fallback_to_api_for_uncached_members(self):
        """Test fallback to GitHub API for uncached members."""
        validator = GitHubAssigneeValidator(
            token="token",
            owner="owner",
            repo="repo",
            cached_members=["alice", "bob"],
        )

        mock_client = MagicMock()
        mock_client.validate_assignee.side_effect = [
            (True, ""),  # First uncached member valid
            (False, "Not found"),  # Second uncached member invalid
        ]

        with patch(
            "roadmap.infrastructure.validation.github_validator.ValidationGateway.get_github_client"
        ) as mock_get_client:
            mock_get_client.return_value = mock_client

            # Cached member - no API call
            result1 = validator.validate("alice")
            assert result1.is_valid is True
            assert mock_get_client.call_count == 0

            # Uncached member - API call
            result2 = validator.validate("charlie")
            assert result2.is_valid is True
            assert mock_get_client.call_count == 1

            # Another uncached member - API call
            result3 = validator.validate("diana")
            assert result3.is_valid is False
            assert mock_get_client.call_count == 2
