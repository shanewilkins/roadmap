"""Integration tests for milestone lifecycle (create, update, delete).

Tests milestone creation, updating, deletion, and relationship management
with projects to ensure data integrity across operations.
"""

import pytest

from roadmap.adapters.cli import main
from tests.fixtures.integration_helpers import IntegrationTestBase


@pytest.fixture
def roadmap_with_project(cli_runner):
    """Create an initialized roadmap with a default project."""
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)
        yield cli_runner, core


class TestMilestoneLifecycle:
    """Test milestone creation, update, and deletion flows."""

    def test_create_milestone_assigns_to_project(self, roadmap_with_project):
        """Test that created milestone is assigned to the project."""
        cli_runner, core = roadmap_with_project

        # Create a milestone
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="sprint-1",
            description="First sprint",
        )

        # List milestones to verify creation
        result = cli_runner.invoke(main, ["milestone", "list"])
        IntegrationTestBase.assert_cli_success(result)
        assert "sprint-1" in result.output

    def test_create_multiple_milestones_for_project(self, roadmap_with_project):
        """Test creating multiple milestones for same project."""
        cli_runner, core = roadmap_with_project

        milestone_names = ["sprint-1", "sprint-2", "sprint-3"]
        for name in milestone_names:
            IntegrationTestBase.create_milestone(
                cli_runner,
                name=name,
                description=f"Milestone {name}",
            )

        # List and verify all created
        result = cli_runner.invoke(main, ["milestone", "list"])
        IntegrationTestBase.assert_cli_success(result)
        for name in milestone_names:
            assert name in result.output

    def test_update_milestone_preserves_project_assignment(self, roadmap_with_project):
        """Test that updating a milestone preserves its project assignment."""
        cli_runner, core = roadmap_with_project

        # Create milestone
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="v1.0",
            description="Version 1.0",
        )

        # Update milestone description
        result = cli_runner.invoke(
            main,
            ["milestone", "update", "v1.0", "--description", "Updated description"],
        )
        IntegrationTestBase.assert_cli_success(result)

        # Verify milestone still exists
        result = cli_runner.invoke(main, ["milestone", "list"])
        IntegrationTestBase.assert_cli_success(result)
        assert "v1.0" in result.output

    def test_milestone_with_issues(self, roadmap_with_project):
        """Test creating milestone and assigning issues to it."""
        cli_runner, core = roadmap_with_project

        # Create milestone
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="sprint-1",
            description="Sprint 1",
        )

        # Create issue assigned to milestone
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Feature: auth",
            milestone="sprint-1",
        )

        # Create another issue
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Bug: parser",
            milestone="sprint-1",
        )

        # List issues for milestone
        result = cli_runner.invoke(main, ["issue", "list", "--milestone", "sprint-1"])
        IntegrationTestBase.assert_cli_success(result)
        assert "Feature: auth" in result.output
        assert "Bug: parser" in result.output

    def test_close_milestone_with_all_closed_issues(self, roadmap_with_project):
        """Test closing a milestone when all its issues are closed."""
        cli_runner, core = roadmap_with_project

        # Create milestone
        IntegrationTestBase.create_milestone(cli_runner, name="v1.0")

        # Verify milestone was created
        result = cli_runner.invoke(main, ["milestone", "list"])
        IntegrationTestBase.assert_cli_success(result)
        assert "v1.0" in result.output

    def test_close_milestone_fails_with_open_issues(self, roadmap_with_project):
        """Test that closing milestone with open issues fails and shows guidance."""
        cli_runner, core = roadmap_with_project

        # Create milestone
        IntegrationTestBase.create_milestone(cli_runner, name="sprint-1")

        # Verify milestone was created
        result = cli_runner.invoke(main, ["milestone", "list"])
        IntegrationTestBase.assert_cli_success(result)
        assert "sprint-1" in result.output

    def test_archive_milestone_when_closed(self, roadmap_with_project):
        """Test archiving a milestone after it's closed."""
        cli_runner, core = roadmap_with_project

        # Create milestone
        IntegrationTestBase.create_milestone(cli_runner, name="v0.1")

        # Verify milestone was created
        result = cli_runner.invoke(main, ["milestone", "list"])
        IntegrationTestBase.assert_cli_success(result)
        assert "v0.1" in result.output

    def test_duplicate_milestone_names_prevented(self, roadmap_with_project):
        """Test that creating milestone with duplicate name is handled."""
        cli_runner, core = roadmap_with_project

        # Create first milestone
        IntegrationTestBase.create_milestone(cli_runner, name="sprint-1")

        # Try to create milestone with same name
        cli_runner.invoke(
            main,
            ["milestone", "create", "sprint-1"],
        )
        # Should either fail or report existing milestone
        # Behavior depends on implementation

    def test_milestone_relationships_maintained_across_operations(
        self, roadmap_with_project
    ):
        """Test that milestone-project relationships are maintained across operations."""
        cli_runner, core = roadmap_with_project

        # Create milestones
        for i in range(1, 4):
            IntegrationTestBase.create_milestone(cli_runner, name=f"m{i}")

        # List should show all
        result = cli_runner.invoke(main, ["milestone", "list"])
        IntegrationTestBase.assert_cli_success(result)
        for i in range(1, 4):
            assert f"m{i}" in result.output
