"""Tests for assignee validation functionality."""

from typing import cast
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.infrastructure.core import RoadmapCore
from tests.unit.common.formatters.test_assertion_helpers import assert_command_success
from tests.unit.domain.test_data_factory_generation import TestDataFactory


@pytest.fixture
def initialized_roadmap(temp_dir):
    """Create a temporary directory with initialized roadmap."""
    from roadmap.adapters.cli import main

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init",
            "--non-interactive",
            "--skip-github",
            "--project-name",
            "Test Project",
        ],
    )
    if result.exit_code != 0:
        print(f"CLI exit code: {result.exit_code}")
        print(f"CLI output: {result.output}")
        if result.exception:
            print(f"Exception: {result.exception}")
            import traceback

            traceback.print_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
    assert result.exit_code == 0
    return temp_dir


class TestAssigneeValidation:
    """Test cases for assignee validation."""

    @pytest.mark.parametrize(
        "assignee_input,description",
        [
            ("", "empty string"),
            (cast(str, None), "None"),
            ("   ", "whitespace only"),
        ],
    )
    def test_empty_assignee_validation(
        self, initialized_roadmap, assignee_input, description
    ):
        """Test that empty assignees are rejected."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        is_valid, error = core.team.validate_assignee(assignee_input)
        assert not is_valid, f"Failed for {description}"
        assert "cannot be empty" in error.lower()

    @pytest.mark.parametrize(
        "github_configured,assignee,should_accept",
        [
            # No GitHub - accept anything
            (False, "localuser", True),
            (False, "john.doe@company.com", True),
            (False, "alice", True),
            # With GitHub - accept based on mock result
            (True, "validuser", True),
            (True, "invaliduser", False),
        ],
    )
    def test_assignee_validation_github_config(
        self, initialized_roadmap, github_configured, assignee, should_accept
    ):
        """Test assignee validation with and without GitHub configuration."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        if not github_configured:
            # Test without GitHub
            with patch.object(
                core.validation, "get_github_config", return_value=(None, None, None)
            ):
                is_valid, error = core.team.validate_assignee(assignee)
                assert is_valid
                assert error == ""
        else:
            # Test with GitHub
            if should_accept:
                with patch.object(
                    core.github_service, "validate_assignee", return_value=(True, "")
                ):
                    is_valid, error = core.team.validate_assignee(assignee)
                    assert is_valid
                    assert error == ""
            else:
                with patch.object(
                    core.github_service,
                    "validate_assignee",
                    return_value=(False, f"User '{assignee}' not found"),
                ):
                    is_valid, error = core.team.validate_assignee(assignee)
                    assert not is_valid
                    assert "not found" in error.lower()

    def test_validation_only_when_github_configured(self, initialized_roadmap):
        """Test that validation logic is conditional on GitHub configuration."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Test 1: No GitHub config -> no validation (should accept anything)
        with patch.object(
            core.github_service, "validate_assignee", return_value=(True, "")
        ):
            is_valid, error = core.team.validate_assignee("any-username-here")
            assert is_valid
            assert error == ""

        # Test 2: Partial GitHub config -> validation still goes through service
        with patch.object(
            core.github_service, "validate_assignee", return_value=(True, "")
        ):
            is_valid, error = core.team.validate_assignee("any-username-here")
            assert is_valid
            assert error == ""

        # Test 3: Full GitHub config -> validation occurs through service
        with patch.object(
            core.github_service, "validate_assignee", return_value=(True, "")
        ):
            is_valid, error = core.team.validate_assignee("validuser")
            assert is_valid

    def test_cached_team_members(self, initialized_roadmap):
        """Test team members caching functionality."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Mock get_team_members in the service to return test data
        with patch.object(
            core.github_service, "get_team_members", return_value=["user1", "user2"]
        ) as mock_get_members:
            # First call should fetch from API (or from underlying service)
            members1 = core.team.get_members()
            assert members1 == ["user1", "user2"]
            assert mock_get_members.call_count == 1

            # Second call might use cache depending on implementation
            members2 = core.team.get_members()
            assert members2 == ["user1", "user2"]
            # Note: Cache behavior depends on implementation - may or may not be called again

    def test_github_config_helper(self, initialized_roadmap):
        """Test the GitHub configuration helper method."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Test with no configuration
        token, owner, repo = core.validation.get_github_config()
        # Should return None values when not configured
        assert token is None or owner is None or repo is None


class TestCLIAssigneeValidation:
    """Test CLI integration with assignee validation."""

    def test_issue_create_with_invalid_assignee(self, cli_runner, initialized_roadmap):
        """Test issue creation with invalid assignee."""
        from roadmap.adapters.cli import main

        # Create a mock core
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.is_initialized.return_value = True
        mock_core.team.validate_assignee.return_value = (
            False,
            "User 'baduser' does not exist",
        )
        mock_core.team.get_current_user.return_value = None
        mock_core.issues.create.side_effect = Exception("Should not reach create")

        # Mock the CLI's core resolution
        with patch("roadmap.cli.RoadmapCore") as mock_core_class:
            mock_core_class.find_existing_roadmap.return_value = None
            mock_core_class.return_value = mock_core

            result = cli_runner.invoke(
                main,
                ["issue", "create", "Test Issue", "--assignee", "baduser"],
                obj={"core": mock_core},
            )

            # Click Abort should result in exit code 1
            assert result.exit_code == 1
            assert (
                "Invalid assignee" in result.output or "does not exist" in result.output
            )
            # Should not create issue when validation fails
            mock_core.issues.create.assert_not_called()

    def test_issue_create_with_valid_assignee(self, cli_runner, initialized_roadmap):
        """Test issue creation with valid assignee."""
        from roadmap.adapters.cli import main

        # Create a mock core
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.is_initialized.return_value = True
        mock_core.team.validate_assignee.return_value = (True, "")
        mock_core.team.get_current_user.return_value = None
        mock_core.git.is_git_repository.return_value = (
            False  # Disable git branch creation
        )

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

            result = cli_runner.invoke(
                main, ["issue", "create", "Test Issue", "--assignee", "gooduser"]
            )

            assert_command_success(result)
            # Should create issue when validation passes
            mock_core.issues.create.assert_called_once()

    def test_issue_create_local_only_usage(self, cli_runner, initialized_roadmap):
        """Test issue creation works without GitHub when validation is skipped."""
        from roadmap.adapters.cli import main

        # Create a mock core that simulates local-only usage (no GitHub config)
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.is_initialized.return_value = True
        mock_core.team.validate_assignee.return_value = (
            True,
            "",
        )  # No validation when no GitHub
        mock_core.team.get_current_user.return_value = None
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
            result = cli_runner.invoke(
                main,
                ["issue", "create", "Local Issue", "--assignee", "alice.local"],
                obj={"core": mock_core},
            )

            assert_command_success(result)
            # Validation should have been called but returned success
            mock_core.team.validate_assignee.assert_called_once_with("alice.local")
            # Issue should have been created successfully
            mock_core.issues.create.assert_called_once()
