"""Tests for assignee validation functionality."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from roadmap.application.core import RoadmapCore


@pytest.fixture
def cli_runner():
    """Create an isolated CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def initialized_roadmap(temp_dir):
    """Create a temporary directory with initialized roadmap."""
    from roadmap.presentation.cli import main

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
    assert result.exit_code == 0
    return temp_dir


class TestAssigneeValidation:
    """Test cases for assignee validation."""

    def test_empty_assignee_validation(self, initialized_roadmap):
        """Test that empty assignees are rejected."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Test empty string
        is_valid, error = core.validate_assignee("")
        assert not is_valid
        assert "cannot be empty" in error.lower()

        # Test None
        is_valid, error = core.validate_assignee(None)
        assert not is_valid
        assert "cannot be empty" in error.lower()

        # Test whitespace
        is_valid, error = core.validate_assignee("   ")
        assert not is_valid
        assert "cannot be empty" in error.lower()

    def test_assignee_validation_without_github(self, initialized_roadmap):
        """Test that any assignee is accepted when GitHub is not configured.

        This supports local-only roadmap usage where users want to assign
        issues without GitHub integration validation.
        """
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Mock no GitHub configuration (local-only usage)
        with patch.object(core, "_get_github_config", return_value=(None, None, None)):
            # Should accept any assignee without validation
            is_valid, error = core.validate_assignee("localuser")
            assert is_valid
            assert error == ""

            # Should also accept usernames that wouldn't exist on GitHub
            is_valid, error = core.validate_assignee("john.doe@company.com")
            assert is_valid
            assert error == ""

            # Should accept simple names
            is_valid, error = core.validate_assignee("alice")
            assert is_valid
            assert error == ""

    def test_assignee_validation_with_github_valid_user(self, initialized_roadmap):
        """Test validation with GitHub configured and valid user."""
        from datetime import datetime
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Mock GitHub configuration
        with patch.object(
            core, "_get_github_config", return_value=("token", "owner", "repo")
        ):
            # Mock cached team members (cache hit)
            core._team_members_cache = ["validuser", "anotheruser"]
            core._cache_timestamp = datetime.now()

            is_valid, error = core.validate_assignee("validuser")
            assert is_valid
            assert error == ""

    def test_assignee_validation_with_github_invalid_user(self, initialized_roadmap):
        """Test validation with GitHub configured and invalid user."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        with patch.object(
            core, "_get_github_config", return_value=("token", "owner", "repo")
        ):
            # Mock empty team members cache (to force GitHub validation)
            with patch.object(core, "_get_cached_team_members", return_value=[]):
                # Mock the GitHubClient constructor to return our mock
                with patch("roadmap.github_client.GitHubClient") as mock_client_class:
                    mock_client = Mock()
                    mock_client.validate_assignee.return_value = (
                        False,
                        "User 'invaliduser' does not exist",
                    )
                    mock_client_class.return_value = mock_client

                    is_valid, error = core.validate_assignee("invaliduser")
                    assert not is_valid
                    assert "does not exist" in error

    def test_validation_only_when_github_configured(self, initialized_roadmap):
        """Test that validation logic is conditional on GitHub configuration."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Test 1: No GitHub config -> no validation (should accept anything)
        with patch.object(core, "_get_github_config", return_value=(None, None, None)):
            is_valid, error = core.validate_assignee("any-username-here")
            assert is_valid
            assert error == ""

        # Test 2: Partial GitHub config -> no validation
        with patch.object(
            core, "_get_github_config", return_value=("token", None, None)
        ):
            is_valid, error = core.validate_assignee("any-username-here")
            assert is_valid
            assert error == ""

        # Test 3: Full GitHub config -> validation occurs
        with patch.object(
            core, "_get_github_config", return_value=("token", "owner", "repo")
        ):
            with patch.object(core, "_get_cached_team_members", return_value=[]):
                # Mock the GitHubClient constructor to return our mock
                with patch("roadmap.github_client.GitHubClient") as mock_client_class:
                    mock_client = Mock()
                    mock_client.validate_assignee.return_value = (True, "")
                    mock_client_class.return_value = mock_client

                    is_valid, error = core.validate_assignee("validuser")
                    assert is_valid
                    # Verify that the GitHub client validation was actually called
                    mock_client.validate_assignee.assert_called_once_with("validuser")

    def test_cached_team_members(self, initialized_roadmap):
        """Test team members caching functionality."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Mock get_team_members to return test data
        with patch.object(
            core, "get_team_members", return_value=["user1", "user2"]
        ) as mock_get_members:
            # First call should fetch from API
            members1 = core._get_cached_team_members()
            assert members1 == ["user1", "user2"]
            assert mock_get_members.call_count == 1

            # Second call should use cache
            members2 = core._get_cached_team_members()
            assert members2 == ["user1", "user2"]
            assert mock_get_members.call_count == 1  # Still only called once

    def test_github_config_helper(self, initialized_roadmap):
        """Test the GitHub configuration helper method."""
        from pathlib import Path

        core = RoadmapCore(Path(initialized_roadmap))

        # Test with no configuration
        token, owner, repo = core._get_github_config()
        # Should return None values when not configured
        assert token is None or owner is None or repo is None


class TestCLIAssigneeValidation:
    """Test CLI integration with assignee validation."""

    def test_issue_create_with_invalid_assignee(self, cli_runner, initialized_roadmap):
        """Test issue creation with invalid assignee."""
        from roadmap.presentation.cli import main

        # Create a mock core
        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.validate_assignee.return_value = (
            False,
            "User 'baduser' does not exist",
        )
        mock_core.get_current_user_from_git.return_value = None
        mock_core.create_issue.side_effect = Exception("Should not reach create_issue")

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
            assert "Invalid assignee" in result.output
            # Should not create issue when validation fails
            mock_core.create_issue.assert_not_called()

    def test_issue_create_with_valid_assignee(self, cli_runner, initialized_roadmap):
        """Test issue creation with valid assignee."""
        from roadmap.presentation.cli import main

        # Create a mock core
        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.validate_assignee.return_value = (True, "")
        mock_core.get_current_user_from_git.return_value = None
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
        mock_core.create_issue.return_value = mock_issue

        # Mock the CLI's core resolution
        with patch("roadmap.cli.RoadmapCore") as mock_core_class:
            mock_core_class.find_existing_roadmap.return_value = None
            mock_core_class.return_value = mock_core

            result = cli_runner.invoke(
                main, ["issue", "create", "Test Issue", "--assignee", "gooduser"]
            )

            assert result.exit_code == 0
            assert "Created issue" in result.output
            # Should create issue when validation passes
            mock_core.create_issue.assert_called_once()

    def test_issue_create_local_only_usage(self, cli_runner, initialized_roadmap):
        """Test issue creation works without GitHub when validation is skipped."""
        from roadmap.presentation.cli import main

        # Create a mock core that simulates local-only usage (no GitHub config)
        mock_core = Mock()
        mock_core.is_initialized.return_value = True
        mock_core.validate_assignee.return_value = (
            True,
            "",
        )  # No validation when no GitHub
        mock_core.get_current_user_from_git.return_value = None
        mock_core.git.is_git_repository.return_value = False

        # Mock successful issue creation
        mock_issue = Mock()
        mock_issue.title = "Local Issue"
        mock_issue.id = "local123"
        mock_issue.issue_type.value.title.return_value = "Other"
        mock_issue.priority.value = "medium"
        mock_issue.filename = "local123-local-issue.md"
        mock_issue.estimated_time_display = "Not estimated"
        mock_core.create_issue.return_value = mock_issue

        with patch("roadmap.cli.RoadmapCore") as mock_core_class:
            mock_core_class.find_existing_roadmap.return_value = None
            mock_core_class.return_value = mock_core

            # Should work with any assignee when GitHub is not configured
            result = cli_runner.invoke(
                main,
                ["issue", "create", "Local Issue", "--assignee", "alice.local"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 0
            assert "Created issue" in result.output
            # Validation should have been called but returned success
            mock_core.validate_assignee.assert_called_once_with("alice.local")
            # Issue should have been created successfully
            mock_core.create_issue.assert_called_once()
