"""Tests for assignee validation strategies."""

from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.assignee_validation_service import (
    AssigneeValidationResult,
    AssigneeValidationStrategy,
    IdentitySystemValidator,
    LocalValidator,
)
from roadmap.infrastructure.github_validator import (
    GitHubAssigneeValidator as GitHubValidator,
)


class TestAssigneeValidationResult:
    """Test the validation result data class."""

    @pytest.mark.parametrize(
        "is_valid,message,canonical_id",
        [
            (True, "", "test_user"),
            (False, "User not found", ""),
        ],
    )
    def test_validation_result_creation(self, is_valid, message, canonical_id):
        """Test creating validation results with various states."""
        result = AssigneeValidationResult(
            is_valid=is_valid, message=message, canonical_id=canonical_id
        )

        assert result.is_valid == is_valid
        assert result.message == message
        assert result.canonical_id == canonical_id


class TestLocalValidator:
    """Test local validation rules."""

    @pytest.mark.parametrize(
        "name",
        [
            "john_doe",
            "alice-smith",
            "bob123",
        ],
    )
    def test_valid_local_assignee(self, name):
        """Test valid local assignee names."""
        validator = LocalValidator()

        result = validator.validate(name)
        assert result.is_valid
        assert result.canonical_id == name

    @pytest.mark.parametrize(
        "invalid_name",
        [
            "a",
            "user<test>",
            "user{test}",
            "user[test]",
            "user(test)",
        ],
    )
    def test_invalid_local_assignee(self, invalid_name):
        """Test invalid assignee names with various issues."""
        validator = LocalValidator()

        result = validator.validate(invalid_name)
        assert not result.is_valid
        assert "not a valid assignee name" in result.message


class TestGitHubValidator:
    """Test GitHub validation."""

    @pytest.mark.parametrize(
        "cached_members,test_name",
        [
            ({"alice", "bob", "charlie"}, "alice"),
            (["alice", "bob", "charlie"], "bob"),
        ],
    )
    def test_cached_member_validation(self, cached_members, test_name):
        """Test validation with cached members."""
        validator = GitHubValidator("token", "owner", "repo", cached_members)

        result = validator.validate(test_name)
        assert result.is_valid
        assert result.canonical_id == test_name

    def test_api_validation_success(self):
        """Test successful API validation."""
        validator = GitHubValidator("token", "owner", "repo", None)

        with patch(
            "roadmap.infrastructure.github_validator.GitHubClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.validate_assignee.return_value = (True, "")
            mock_client_class.return_value = mock_client

            result = validator.validate("newuser")
            assert result.is_valid
            assert result.canonical_id == "newuser"

    def test_api_validation_failure(self):
        """Test failed API validation."""
        validator = GitHubValidator("token", "owner", "repo", None)

        with patch(
            "roadmap.infrastructure.github_validator.GitHubClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.validate_assignee.return_value = (
                False,
                "User does not exist",
            )
            mock_client_class.return_value = mock_client

            result = validator.validate("invaliduser")
            assert not result.is_valid
            assert "does not exist" in result.message

    def test_api_validation_exception(self):
        """Test API validation with exception."""
        validator = GitHubValidator("token", "owner", "repo", None)

        with patch(
            "roadmap.infrastructure.github_validator.GitHubClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Network error")

            result = validator.validate("testuser")
            assert not result.is_valid
            assert "GitHub validation failed" in result.message


class TestIdentitySystemValidator:
    """Test identity system validation (system not implemented yet)."""

    def test_identity_system_unavailable(self, tmp_path):
        """Test when identity system is not available (current state)."""
        validator = IdentitySystemValidator(str(tmp_path))

        # Since identity system doesn't exist in main codebase yet,
        # this should always return unavailable marker
        result = validator.validate("testuser")
        assert not result.is_valid
        assert result.canonical_id == "identity-unavailable"

    def test_get_validation_mode_fallback(self, tmp_path):
        """Test validation mode fallback when unavailable (current state)."""
        validator = IdentitySystemValidator(str(tmp_path))

        # Should return fallback mode since identity system not implemented
        mode = validator.get_validation_mode()
        assert mode == "local-only"


class TestAssigneeValidationStrategy:
    """Test the validation strategy orchestration."""

    def test_empty_assignee(self, tmp_path):
        """Test validation with empty assignee."""
        strategy = AssigneeValidationStrategy(str(tmp_path))

        is_valid, error, canonical = strategy.validate("")
        assert not is_valid
        assert error == "Assignee cannot be empty"

        is_valid, error, canonical = strategy.validate("   ")
        assert not is_valid
        assert error == "Assignee cannot be empty"

    def test_identity_system_success(self, tmp_path):
        """Test successful validation through identity system."""
        strategy = AssigneeValidationStrategy(str(tmp_path))

        with patch.object(
            strategy.identity_validator, "validate"
        ) as mock_identity_validate:
            mock_identity_validate.return_value = AssigneeValidationResult(
                is_valid=True, canonical_id="alice@company.com"
            )

            is_valid, error, canonical = strategy.validate("alice")
            assert is_valid
            assert error == ""
            assert canonical == "alice@company.com"

    def test_identity_unavailable_github_success(self, tmp_path):
        """Test GitHub fallback when identity system unavailable."""
        github_config = ("token", "owner", "repo")
        cached_members = {"alice", "bob"}
        strategy = AssigneeValidationStrategy(
            str(tmp_path), github_config, cached_members
        )

        with patch.object(
            strategy.identity_validator, "validate"
        ) as mock_identity_validate:
            # Simulate identity system unavailable
            mock_identity_validate.return_value = AssigneeValidationResult(
                is_valid=False, canonical_id="identity-unavailable"
            )

            is_valid, error, canonical = strategy.validate("alice")
            assert is_valid
            assert canonical == "alice"

    def test_identity_unavailable_local_fallback(self, tmp_path):
        """Test local fallback when identity and GitHub unavailable."""
        strategy = AssigneeValidationStrategy(str(tmp_path), None, None)

        with patch.object(
            strategy.identity_validator, "validate"
        ) as mock_identity_validate:
            # Simulate identity system unavailable
            mock_identity_validate.return_value = AssigneeValidationResult(
                is_valid=False, canonical_id="identity-unavailable"
            )

            is_valid, error, canonical = strategy.validate("john_doe")
            assert is_valid
            assert canonical == "john_doe"

    def test_github_validation_mode_hybrid(self, tmp_path):
        """Test hybrid mode with GitHub validation."""
        github_config = ("token", "owner", "repo")
        strategy = AssigneeValidationStrategy(str(tmp_path), github_config, None)

        with patch.object(
            strategy.identity_validator, "validate"
        ) as mock_identity_validate:
            # Identity system fails but in hybrid mode
            mock_identity_validate.return_value = AssigneeValidationResult(
                is_valid=False, message="Not found", canonical_id="hybrid"
            )

            with patch(
                "roadmap.infrastructure.github_validator.GitHubClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.validate_assignee.return_value = (True, "")
                mock_client_class.return_value = mock_client

                is_valid, error, canonical = strategy.validate("testuser")
                assert is_valid
                assert canonical == "testuser"

    def test_github_only_mode_failure(self, tmp_path):
        """Test github-only mode returns GitHub error."""
        github_config = ("token", "owner", "repo")
        strategy = AssigneeValidationStrategy(str(tmp_path), github_config, None)

        with patch.object(
            strategy.identity_validator, "validate"
        ) as mock_identity_validate:
            # Identity system fails in github-only mode
            mock_identity_validate.return_value = AssigneeValidationResult(
                is_valid=False, message="Not found", canonical_id="github-only"
            )

            with patch(
                "roadmap.infrastructure.github_validator.GitHubClient"
            ) as mock_client_class:
                mock_client = Mock()
                mock_client.validate_assignee.return_value = (
                    False,
                    "User not in repo",
                )
                mock_client_class.return_value = mock_client

                is_valid, error, canonical = strategy.validate("baduser")
                assert not is_valid
                assert "not in repo" in error

    def test_local_validation_mode(self, tmp_path):
        """Test local-only validation mode."""
        strategy = AssigneeValidationStrategy(str(tmp_path), None, None)

        with patch.object(
            strategy.identity_validator, "validate"
        ) as mock_identity_validate:
            # Identity fails but in local-only mode
            mock_identity_validate.return_value = AssigneeValidationResult(
                is_valid=False, message="Not found", canonical_id="local-only"
            )

            is_valid, error, canonical = strategy.validate("localuser")
            assert is_valid
            assert canonical == "localuser"

    def test_local_validation_invalid(self, tmp_path):
        """Test local validation with invalid name."""
        strategy = AssigneeValidationStrategy(str(tmp_path), None, None)

        with patch.object(
            strategy.identity_validator, "validate"
        ) as mock_identity_validate:
            mock_identity_validate.return_value = AssigneeValidationResult(
                is_valid=False, canonical_id="local-only"
            )

            is_valid, error, canonical = strategy.validate("a")
            assert not is_valid
            assert "not a valid assignee name" in error

    def test_should_use_github_validation(self, tmp_path):
        """Test _should_use_github_validation logic."""
        # No GitHub config
        strategy = AssigneeValidationStrategy(str(tmp_path), None, None)
        assert not strategy._should_use_github_validation("hybrid")

        # GitHub config but not in hybrid/github-only mode
        github_config = ("token", "owner", "repo")
        strategy = AssigneeValidationStrategy(str(tmp_path), github_config, None)
        assert not strategy._should_use_github_validation("local-only")
        assert strategy._should_use_github_validation("hybrid")
        assert strategy._should_use_github_validation("github-only")

    def test_should_use_local_validation(self, tmp_path):
        """Test _should_use_local_validation logic."""
        # No GitHub config, local mode
        strategy = AssigneeValidationStrategy(str(tmp_path), None, None)
        assert strategy._should_use_local_validation("local-only")
        assert strategy._should_use_local_validation("hybrid")

        # GitHub configured
        github_config = ("token", "owner", "repo")
        strategy = AssigneeValidationStrategy(str(tmp_path), github_config, None)
        assert not strategy._should_use_local_validation("hybrid")
        assert not strategy._should_use_local_validation("local-only")
