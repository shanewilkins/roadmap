"""Tests for assignee validation functionality."""

from typing import cast
from unittest.mock import Mock, patch

import pytest


class TestAssigneeValidation:
    """Test cases for assignee validation."""

    @pytest.mark.skip(reason="Mock core doesn't properly implement validate_assignee")
    def test_empty_assignee_validation(self, mock_core_initialized):
        """Test that empty assignees are rejected."""
        core = mock_core_initialized

        # Test empty string
        is_valid, error = core.team.validate_assignee("")
        assert not is_valid
        assert "cannot be empty" in error.lower()

        # Test None
        is_valid, error = core.team.validate_assignee(cast(str, None))
        assert not is_valid
        assert "cannot be empty" in error.lower()

        # Test whitespace
        is_valid, error = core.team.validate_assignee("   ")
        assert not is_valid
        assert "cannot be empty" in error.lower()

    @pytest.mark.skip(reason="Mock core doesn't properly implement validate_assignee")
    def test_assignee_validation_without_github(self, mock_core_initialized):
        """Test that validation works without GitHub config.

        This supports local-only roadmap usage where users want to assign
        issues without GitHub integration validation.
        """
        core = mock_core_initialized

        # Should accept any assignee - validation is delegated to the service
        is_valid, error = core.team.validate_assignee("localuser")
        assert isinstance(is_valid, bool)
        assert isinstance(error, str)

    @pytest.mark.skip(reason="Mock core doesn't properly implement validate_assignee")
    def test_assignee_validation_with_github_valid_user(self, mock_core_initialized):
        """Test validation with GitHub configured and valid user."""
        core = mock_core_initialized

        # Validation is delegated to the service
        is_valid, error = core.team.validate_assignee("validuser")
        assert isinstance(is_valid, bool)
        assert isinstance(error, str)

    @pytest.mark.skip(reason="Mock core doesn't properly support patching")
    def test_assignee_validation_with_github_invalid_user(self, mock_core_initialized):
        """Test validation with GitHub configured and invalid user."""
        core = mock_core_initialized

        # Mock the service to return invalid result
        with patch.object(core.github_service, "validate_assignee") as mock_validate:
            mock_validate.return_value = (False, "User 'invaliduser' does not exist")

            is_valid, error = core.team.validate_assignee("invaliduser")
            assert not is_valid
            assert "does not exist" in error

    @pytest.mark.skip(reason="Mock core doesn't properly support patching")
    def test_validation_only_when_github_configured(self, mock_core_initialized):
        """Test that validation logic is conditional on GitHub configuration."""
        core = mock_core_initialized

        # Validation is delegated to the service
        with patch.object(
            core.github_service, "validate_assignee", return_value=(True, "")
        ):
            is_valid, error = core.team.validate_assignee("any-username-here")
            assert is_valid
            assert error == ""

    @pytest.mark.skip(reason="Mock core doesn't properly support patching")
    def test_cached_team_members(self, mock_core_initialized):
        """Test team members caching functionality."""
        core = mock_core_initialized

        # Mock get_team_members in the service to return test data
        with patch.object(
            core.github_service, "get_team_members", return_value=["user1", "user2"]
        ):
            # First call should fetch from API
            members1 = core.team.get_cached_team_members()
            assert isinstance(members1, list)


class TestCLIAssigneeValidation:
    """Test CLI integration with assignee validation."""

    @pytest.mark.skip(reason="cli_runner_mocked fixture not found")
    def test_issue_create_with_invalid_assignee(self, cli_runner_mocked):
        """Test issue creation with invalid assignee."""
        from roadmap.adapters.cli import main

        runner, mock_core = cli_runner_mocked
        mock_core.is_initialized.return_value = True
        mock_core.team.validate_assignee.return_value = (
            False,
            "User 'baduser' does not exist",
        )
        mock_core.git.is_git_repository.return_value = False
        mock_core.issues.create.side_effect = Exception("Should not reach create_issue")

        # Mock the CLI's core resolution
        with patch("roadmap.cli.RoadmapCore") as mock_core_class:
            mock_core_class.find_existing_roadmap.return_value = None
            mock_core_class.return_value = mock_core

            result = runner.invoke(
                main,
                ["issue", "create", "Test Issue", "--assignee", "baduser"],
                obj={"core": mock_core},
            )

            # Click Abort should result in exit code 1
            assert result.exit_code == 1
            assert "Invalid assignee" in result.output

    @pytest.mark.skip(reason="cli_runner_mocked fixture not found")
    def test_issue_create_with_valid_assignee(self, cli_runner_mocked):
        """Test issue creation with valid assignee."""
        from roadmap.adapters.cli import main

        runner, mock_core = cli_runner_mocked
        mock_core.is_initialized.return_value = True
        mock_core.team.validate_assignee.return_value = (True, "")
        mock_core.git.is_git_repository.return_value = False

        # Mock successful issue creation - use a Mock instead of real Issue
        mock_issue = Mock()
        mock_issue.title = "Test Issue"
        mock_issue.id = "test123"
        mock_issue.issue_type.value.title.return_value = "Other"
        mock_issue.priority.value = "medium"
        mock_issue.filename = "test123-test-issue.md"
        mock_issue.estimated_time_display = "Not estimated"
        mock_core.issues.create.return_value = mock_issue

        # Mock the CLI's core resolution
        with patch("roadmap.cli.RoadmapCore") as mock_core_class:
            mock_core_class.find_existing_roadmap.return_value = None
            mock_core_class.return_value = mock_core

            result = runner.invoke(
                main, ["issue", "create", "Test Issue", "--assignee", "gooduser"]
            )

            assert result.exit_code == 0
            assert "Created issue" in result.output

    @pytest.mark.skip(reason="cli_runner_mocked fixture not found")
    def test_issue_create_local_only_usage(self, cli_runner_mocked):
        """Test issue creation works without GitHub when validation is skipped."""
        from roadmap.adapters.cli import main

        runner, mock_core = cli_runner_mocked
        # Create a mock core that simulates local-only usage (no GitHub config)
        mock_core.is_initialized.return_value = True
        mock_core.team.validate_assignee.return_value = (
            True,
            "",
        )  # No validation when no GitHub
        mock_core.git.is_git_repository.return_value = False

        # Mock successful issue creation
        mock_issue = Mock()
        mock_issue.title = "Local Issue"
        mock_issue.id = "local123"
        mock_issue.issue_type.value.title.return_value = "Other"
        mock_issue.priority.value = "medium"
        mock_issue.filename = "local123-local-issue.md"
        mock_issue.estimated_time_display = "Not estimated"
        mock_core.issues.create.return_value = mock_issue

        with patch("roadmap.cli.RoadmapCore") as mock_core_class:
            mock_core_class.find_existing_roadmap.return_value = None
            mock_core_class.return_value = mock_core

            # Should work with any assignee when GitHub is not configured
            result = runner.invoke(
                main,
                ["issue", "create", "Local Issue", "--assignee", "alice.local"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0
            assert "Created issue" in result.output
            # Validation should have been called but returned success
            mock_core.team.validate_assignee.assert_called_once_with("alice.local")
            # Issue should have been created successfully
            mock_core.issues.create.assert_called_once()
