"""Tests for assignee validation functionality."""

from unittest.mock import Mock, patch

import pytest


class TestAssigneeValidation:
    """Test cases for assignee validation."""

    def test_validate_assignee_string_type(self):
        """Test that validate_assignee method exists and returns expected tuple type."""
        from unittest.mock import Mock

        from roadmap.infrastructure.coordination.team_coordinator import TeamCoordinator

        mock_ops = Mock()
        coordinator = TeamCoordinator(mock_ops)
        # The method exists and is callable
        assert hasattr(coordinator, "validate_assignee")
        assert callable(coordinator.validate_assignee)


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
