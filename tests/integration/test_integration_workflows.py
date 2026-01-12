"""
Integration tests for the roadmap CLI tool.

These tests verify end-to-end workflows and cross-module integration.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.core.domain import Status
from roadmap.infrastructure.core import RoadmapCore
from tests.unit.shared.test_helpers import (
    assert_command_success,
    assert_issue_created,
    assert_milestone_created,
)

pytestmark = pytest.mark.filesystem


@pytest.fixture
def mock_github_client():
    """Mock GitHub client for integration operations."""
    with patch("roadmap.adapters.github.github.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock successful API responses
        mock_client.test_connection.return_value = (True, "Connected successfully")
        mock_client.create_issue.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/repo/issues/1",
        }
        mock_client.update_issue.return_value = {"number": 1}
        mock_client.create_milestone.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/repo/milestones/1",
        }
        mock_client.get_issues.return_value = []
        mock_client.get_milestones.return_value = []

        yield mock_client


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def test_complete_roadmap_lifecycle(self, tmp_path):
        """Test a complete roadmap lifecycle from init to issue management."""
        # CRITICAL: This test must use tmp_path (clean) instead of temp_workspace (pre-initialized)
        # because it needs to test the full initialization workflow starting from an empty directory.
        # The test verifies that 'roadmap init' creates the proper directory structure and config.
        os.chdir(tmp_path)
        runner = CliRunner()
        core = RoadmapCore()

        # Step 1: Initialize roadmap
        result = runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "Test Lifecycle",
            ],
        )
        assert_command_success(result)
        assert os.path.exists(".roadmap")
        assert os.path.exists(".roadmap/config.yaml")

        # Step 2: Check status of empty roadmap (via database)
        result = runner.invoke(main, ["status"])
        assert_command_success(result)

        # Step 3: Create multiple issues (verify via database, not output)
        issue_titles = ["Implement feature A", "Fix bug B", "Add documentation C"]

        for i, title in enumerate(issue_titles):
            priority = ["low", "medium", "high"][i % 3]
            result = runner.invoke(
                main, ["issue", "create", title, "--priority", priority]
            )
            assert_command_success(result)

        # Verify issues were created by checking database
        issues = core.issues.list()
        assert len(issues) == 3
        for title in issue_titles:
            assert_issue_created(core, title)

        # Step 4: Create milestones (verify via database)
        milestone_titles = ["Version 1.0", "Version 1.1"]

        for title in milestone_titles:
            result = runner.invoke(main, ["milestone", "create", title])
            assert_command_success(result)

        # Verify milestones were created by checking database
        milestones = core.milestones.list()
        assert len(milestones) == 2
        for title in milestone_titles:
            assert_milestone_created(core, title)

        # Step 5: Assign issues to milestones
        issue_objects = core.issues.list()
        milestone_objects = core.milestones.list()

        result = runner.invoke(
            main,
            [
                "milestone",
                "assign",
                str(issue_objects[0].id),
                milestone_objects[0].name,
            ],
        )
        assert_command_success(result)

        result = runner.invoke(
            main,
            [
                "milestone",
                "assign",
                str(issue_objects[1].id),
                milestone_objects[0].name,
            ],
        )
        assert_command_success(result)

        result = runner.invoke(
            main,
            [
                "milestone",
                "assign",
                str(issue_objects[2].id),
                milestone_objects[1].name,
            ],
        )
        assert_command_success(result)

        # Verify assignments via database
        # Clear the list cache to ensure we get fresh data after CLI operations
        core.issues._ops.issue_service._list_issues_cache.clear()
        for issue in core.issues.list():
            assert issue.milestone is not None

        # Step 6: Update issue status
        result = runner.invoke(
            main,
            ["issue", "update", str(issue_objects[0].id), "--status", "in-progress"],
        )
        assert_command_success(result)

        # Verify status update via database
        updated_issue = core.issues.get(issue_objects[0].id)
        assert updated_issue is not None
        assert str(updated_issue.status.value) == "in-progress"

        # Step 7: List issues with filters
        result = runner.invoke(main, ["issue", "list", "--status", "in-progress"])
        assert_command_success(result)

        result = runner.invoke(main, ["issue", "list", "--priority", "high"])
        assert_command_success(result)

        # Step 8: Check final status
        result = runner.invoke(main, ["status"])
        assert_command_success(result)

        # Step 9: Delete an issue
        issue_objects_for_delete = core.issues.list()
        result = runner.invoke(
            main, ["issue", "delete", str(issue_objects_for_delete[2].id)], input="y\n"
        )
        assert result.exit_code == 0
        assert "Deleted" in result.output or "deleted" in result.output

        # Step 10: Verify deletion
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        # Verify there's still content but fewer issues
        assert "issue" in result.output.lower() or "milestone" in result.output.lower()

    def test_roadmap_file_persistence(self, temp_workspace):
        """Test that roadmap data persists correctly across operations."""
        runner = CliRunner()

        # Initialize and create some data
        runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )
        runner.invoke(main, ["issue", "create", "Test issue"])
        runner.invoke(main, ["milestone", "create", "Test milestone"])

        # Verify data exists
        core = RoadmapCore()
        assert core.is_initialized()

        issues = core.issues.list()
        milestones = core.milestones.list()

        assert len(issues) == 1
        assert len(milestones) == 1
        assert issues[0].title == "Test issue"
        assert milestones[0].name == "Test milestone"

        # Create a new core instance (simulating restart)
        core2 = RoadmapCore()

        issues2 = core2.issues.list()
        milestones2 = core2.milestones.list()

        assert len(issues2) == 1
        assert len(milestones2) == 1
        assert issues2[0].title == "Test issue"
        assert milestones2[0].name == "Test milestone"

    def test_configuration_management(self, temp_workspace):
        """Test configuration file creation and management."""
        runner = CliRunner()

        # Initialize roadmap
        result = runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )
        assert result.exit_code == 0

        # Check config file exists and has correct structure
        config_path = Path(".roadmap/config.yaml")
        assert config_path.exists()

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Check that config has expected structure
        assert isinstance(config, dict)

        # Test that operations work with existing config
        result = runner.invoke(main, ["issue", "create", "Test issue"])
        assert result.exit_code == 0

        # Verify config is preserved after operations
        with open(config_path) as f:
            config_after = yaml.safe_load(f)

        assert config_after == config

    def test_issue_milestone_relationship(self, temp_workspace):
        """Test the relationship between issues and milestones."""
        runner = CliRunner()

        # Setup
        runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )

        # Create issues
        from tests.fixtures.click_testing import ClickTestHelper

        result = runner.invoke(main, ["issue", "create", "Issue 1"])
        issue1_id = ClickTestHelper.extract_issue_id(result.output)
        assert issue1_id is not None, "Failed to parse issue1_id from output"

        result = runner.invoke(main, ["issue", "create", "Issue 2"])
        issue2_id = ClickTestHelper.extract_issue_id(result.output)
        assert issue2_id is not None, "Failed to parse issue2_id from output"

        result = runner.invoke(main, ["issue", "create", "Backlog Issue"])
        backlog_issue_id = ClickTestHelper.extract_issue_id(result.output)
        assert (
            backlog_issue_id is not None
        ), "Failed to parse backlog_issue_id from output"

        # Create milestone
        milestone_name = "Milestone 1"
        result = runner.invoke(main, ["milestone", "create", milestone_name])
        assert result.exit_code == 0

        # Assign some issues to milestone, leave one in backlog
        runner.invoke(main, ["milestone", "assign", issue1_id, milestone_name])
        runner.invoke(main, ["milestone", "assign", issue2_id, milestone_name])
        # backlog_issue_id intentionally not assigned

        # Verify relationships through core
        core = RoadmapCore()

        # Test milestone methods
        all_issues = core.issues.list()
        milestone = core.milestones.get(milestone_name)

        assert len(all_issues) == 3
        assert milestone is not None

        # Test milestone-issue relationship
        milestone_issues = milestone.get_issues(all_issues)
        assert len(milestone_issues) == 2
        milestone_issue_ids = [issue.id for issue in milestone_issues]
        assert issue1_id in milestone_issue_ids
        assert issue2_id in milestone_issue_ids
        assert backlog_issue_id not in milestone_issue_ids

        # Test backlog functionality
        backlog_issues = core.issues.get_backlog()
        assert len(backlog_issues) == 1
        assert backlog_issues[0].id == backlog_issue_id
        assert backlog_issues[0].is_backlog
        assert backlog_issues[0].milestone_name == "Backlog"

        # Test issues grouped by milestone
        grouped = core.get_issues_by_milestone()
        assert "Backlog" in grouped
        assert milestone_name in grouped
        assert len(grouped["Backlog"]) == 1
        assert len(grouped[milestone_name]) == 2

        # Test milestone completion tracking
        completion_percentage = milestone.get_completion_percentage(all_issues)
        assert completion_percentage == 0.0  # No issues completed yet

        # Update one issue to done and check completion
        core.issues.update(issue1_id, status=Status.CLOSED)
        all_issues = core.issues.list()  # Refresh
        completion_percentage = milestone.get_completion_percentage(all_issues)
        assert completion_percentage == 50.0  # 1 of 2 issues completed

    def test_error_recovery_workflow(self, tmp_path):
        """Test error handling and recovery in workflows."""
        # CRITICAL: This test must use tmp_path (clean) instead of temp_workspace (pre-initialized)
        # because it needs to test error conditions when the roadmap is NOT initialized.
        # The test verifies proper error messages when operations are attempted without initialization.
        os.chdir(tmp_path)
        runner = CliRunner()

        # Test operations without initialization
        result = runner.invoke(main, ["issue", "create", "Test"])
        assert result.exit_code != 0
        assert "Roadmap not initialized" in result.output

        result = runner.invoke(main, ["status"])
        assert result.exit_code != 0
        assert "Roadmap not initialized" in result.output

        # Initialize and test invalid operations
        runner.invoke(
            main,
            [
                "init",
                "--non-interactive",
                "--skip-github",
                "--project-name",
                "test-project",
            ],
        )

        # Try to update non-existent issue
        result = runner.invoke(
            main, ["issue", "update", "nonexistent", "--status", "closed"]
        )
        # Should fail with non-zero exit code for error
        assert result.exit_code != 0 or "Issue not found" in result.output

        # Try to assign to non-existent milestone
        runner.invoke(main, ["issue", "create", "Test issue"])
        result = runner.invoke(main, ["milestone", "assign", "nonexistent", "test-id"])
        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "Failed to assign" in result.output
            or "not found" in result.output.lower()
        )

        # Try to delete non-existent issue
        result = runner.invoke(main, ["issue", "delete", "nonexistent"], input="y\n")
        # Should fail with non-zero exit code when issue not found
        assert result.exit_code != 0 or "not found" in result.output.lower()
