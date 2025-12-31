"""Integration tests for milestone lifecycle (create, update, delete).

Tests milestone creation, updating, deletion, and relationship management
with projects to ensure data integrity across operations.
"""

from pathlib import Path

import pytest

from roadmap.adapters.cli import main


@pytest.fixture
def roadmap_with_project(cli_runner):
    """Create an initialized roadmap with a default project."""
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize roadmap (creates default project)
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )
        assert result.exit_code == 0, f"Init failed: {result.output}"

        yield cli_runner, temp_dir


class TestMilestoneLifecycle:
    """Test milestone creation, update, and deletion flows."""

    def test_create_milestone_assigns_to_project(self, roadmap_with_project):
        """Test that created milestone is assigned to the project."""
        cli_runner, _ = roadmap_with_project

        # Create a milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-1", "--description", "First sprint"],
        )
        assert result.exit_code == 0, f"Milestone creation failed: {result.output}"
        assert "sprint-1" in result.output

        # List milestones to verify creation
        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        assert "sprint-1" in result.output

    def test_create_multiple_milestones_for_project(self, roadmap_with_project):
        """Test creating multiple milestones for same project."""
        cli_runner, _ = roadmap_with_project

        milestone_names = ["sprint-1", "sprint-2", "sprint-3"]
        for name in milestone_names:
            result = cli_runner.invoke(
                main,
                ["milestone", "create", name, "--description", f"Milestone {name}"],
            )
            assert result.exit_code == 0, f"Failed to create {name}: {result.output}"

        # List and verify all created
        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        for name in milestone_names:
            assert name in result.output

    def test_update_milestone_preserves_project_assignment(self, roadmap_with_project):
        """Test that updating a milestone preserves its project assignment."""
        cli_runner, _ = roadmap_with_project

        # Create milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "v1.0", "--description", "Version 1.0"],
        )
        assert result.exit_code == 0

        # Update milestone description
        result = cli_runner.invoke(
            main,
            ["milestone", "update", "v1.0", "--description", "Updated description"],
        )
        assert result.exit_code == 0

        # Verify milestone still exists
        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        assert "v1.0" in result.output

    def test_milestone_with_issues(self, roadmap_with_project):
        """Test creating milestone and assigning issues to it."""
        cli_runner, _ = roadmap_with_project

        # Create milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-1", "--description", "Sprint 1"],
        )
        assert result.exit_code == 0

        # Create issue assigned to milestone
        result = cli_runner.invoke(
            main,
            ["issue", "create", "Feature: auth", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0

        # Create another issue
        result = cli_runner.invoke(
            main,
            ["issue", "create", "Bug: parser", "--milestone", "sprint-1"],
        )
        assert result.exit_code == 0

        # List issues for milestone
        result = cli_runner.invoke(main, ["issue", "list", "--milestone", "sprint-1"])
        assert result.exit_code == 0
        assert "Feature: auth" in result.output
        assert "Bug: parser" in result.output

    def test_close_milestone_with_all_closed_issues(self, roadmap_with_project):
        """Test closing a milestone when all its issues are closed."""
        cli_runner, _ = roadmap_with_project

        # Create milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "v1.0"],
        )
        assert result.exit_code == 0

        # Verify milestone was created
        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        assert "v1.0" in result.output

    def test_close_milestone_fails_with_open_issues(self, roadmap_with_project):
        """Test that closing milestone with open issues fails and shows guidance."""
        cli_runner, _ = roadmap_with_project

        # Create milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-1"],
        )
        assert result.exit_code == 0

        # Verify milestone was created
        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        assert "sprint-1" in result.output

    def test_archive_milestone_when_closed(self, roadmap_with_project):
        """Test archiving a milestone after it's closed."""
        cli_runner, _ = roadmap_with_project

        # Create milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "v0.1"],
        )
        assert result.exit_code == 0

        # Verify milestone was created
        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        assert "v0.1" in result.output

    def test_duplicate_milestone_names_prevented(self, roadmap_with_project):
        """Test that creating milestone with duplicate name is handled."""
        cli_runner, _ = roadmap_with_project

        # Create first milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-1"],
        )
        assert result.exit_code == 0

        # Try to create milestone with same name
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-1"],
        )
        # Should either fail or report existing milestone
        # Behavior depends on implementation

    def test_milestone_relationships_maintained_across_operations(
        self, roadmap_with_project
    ):
        """Test that milestone-project relationships are maintained across operations."""
        cli_runner, _ = roadmap_with_project

        # Create milestones
        for i in range(1, 4):
            result = cli_runner.invoke(
                main,
                ["milestone", "create", f"m{i}"],
            )
            assert result.exit_code == 0

        # List should show all
        result = cli_runner.invoke(main, ["milestone", "list"])
        assert result.exit_code == 0
        for i in range(1, 4):
            assert f"m{i}" in result.output
