"""Integration tests for view commands (issue view, milestone view, project view).

Tests the detailed view commands that display formatted information about individual items.
"""

import re
from datetime import datetime, timedelta

import pytest

from roadmap.adapters.cli import main
from tests.common.cli_test_helpers import CLIOutputParser
from tests.fixtures.integration_helpers import IntegrationTestBase


@pytest.fixture
def roadmap_with_data(cli_runner):
    """Create an isolated roadmap with issues, milestones, and projects.

    Yields:
        tuple: (cli_runner, data_dict)
    """
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)

        # Create a milestone
        IntegrationTestBase.create_milestone(
            cli_runner,
            name="v1.0.0",
            description="First release",
            due_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        )

        # Create an issue
        IntegrationTestBase.create_issue(
            cli_runner,
            title="Test issue for viewing",
            issue_type="feature",
            priority="high",
            milestone="v1.0.0",
        )

        # Get the first issue ID from core
        issues = core.issues.list()
        issue_id = issues[0].id if issues else None
        assert issue_id, "Could not create issue"

        # Create a project
        result = cli_runner.invoke(
            main,
            [
                "project",
                "create",
                "test-project",
                "--description",
                "A test project",
            ],
        )
        assert result.exit_code == 0, f"Project creation failed: {result.output}"

        # Extract project ID using JSON format for robustness
        result = cli_runner.invoke(main, ["project", "list", "--format", "json"])
        assert result.exit_code == 0, f"Project list failed: {result.output}"

        json_output = CLIOutputParser.extract_json(result.output)

        # The JSON output is a TableData structure with "rows" containing the actual data
        # Each row is a list matching the columns in order
        if isinstance(json_output, list):
            # If it's a list, we can't extract rows/columns like this
            # This is likely an error in the test or output format
            pytest.fail(f"Expected dict but got list from JSON output: {json_output}")

        rows = json_output.get("rows", [])
        columns = json_output.get("columns", [])

        # Find the column index for "title"
        title_idx = None
        id_idx = 0  # ID is typically the first column
        for i, col in enumerate(columns):
            if col.get("name") == "title":
                title_idx = i
            elif col.get("name") == "id":
                id_idx = i

        assert title_idx is not None, "Could not find 'title' column in project list"

        # Find the row with title "test-project"
        project_id = None
        for row in rows:
            if row[title_idx] == "test-project":
                project_id = row[id_idx]
                break

        assert project_id, "Could not find project 'test-project' in JSON output"

        yield (
            cli_runner,
            {
                "issue_id": issue_id,
                "milestone_name": "v1.0.0",
                "project_id": project_id,
            },
        )


class TestIssueViewCommand:
    """Test the 'roadmap issue view' command."""

    # Use TestDataFactory for all test data in this class

    def test_issue_view_displays_basic_info(self, roadmap_with_data):
        """Test that issue view displays basic issue information."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", data["issue_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0, f"Issue view failed: {result.output}"
        assert "Test issue for viewing" in result.output
        assert data["issue_id"] in result.output
        assert "high" in result.output.lower() or "HIGH" in result.output

    def test_issue_view_displays_milestone(self, roadmap_with_data):
        """Test that issue view displays associated milestone."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", data["issue_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "v1.0.0" in result.output

    def test_issue_view_displays_type(self, roadmap_with_data):
        """Test that issue view displays the type."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", data["issue_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "feature" in result.output.lower() or "FEATURE" in result.output

    def test_issue_view_nonexistent_issue(self, roadmap_with_data):
        """Test viewing a non-existent issue."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["issue", "view", "00000000-0000-0000-0000-000000000000"]
        )

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )


class TestMilestoneViewCommand:
    """Test the 'roadmap milestone view' command."""

    # Use TestDataFactory for all test data in this class

    def test_milestone_view_displays_basic_info(self, roadmap_with_data):
        """Test that milestone view displays basic milestone information."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["milestone", "view", data["milestone_name"]], catch_exceptions=False
        )

        assert result.exit_code == 0, f"Milestone view failed: {result.output}"
        assert "v1.0.0" in result.output
        assert "First release" in result.output

    def test_milestone_view_displays_progress(self, roadmap_with_data):
        """Test that milestone view displays progress information."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["milestone", "view", data["milestone_name"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should show progress (0/1 or similar since we created 1 issue)
        assert re.search(r"\d+/\d+", result.output), "Progress count not found"

    def test_milestone_view_displays_issues(self, roadmap_with_data):
        """Test that milestone view displays associated issues."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["milestone", "view", data["milestone_name"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Test issue" in result.output  # Title may be split across lines in table

    def test_milestone_view_nonexistent_milestone(self, roadmap_with_data):
        """Test viewing a non-existent milestone."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(main, ["milestone", "view", "v99.99.99"])

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )


class TestProjectViewCommand:
    """Test the 'roadmap project view' command."""

    # Use TestDataFactory for all test data in this class

    def test_project_view_displays_basic_info(self, roadmap_with_data):
        """Test that project view displays basic project information."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["project", "view", data["project_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0, f"Project view failed: {result.output}"
        # Check for the project name we created
        assert "test-project" in result.output
        # Check for the project ID
        assert data["project_id"] in result.output

    def test_project_view_displays_description(self, roadmap_with_data):
        """Test that project view displays the description."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(
            main, ["project", "view", data["project_id"]], catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "A test project" in result.output

    def test_project_view_nonexistent_project(self, roadmap_with_data):
        """Test viewing a non-existent project."""
        cli_runner, data = roadmap_with_data

        result = cli_runner.invoke(main, ["project", "view", "nonexistent-project"])

        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
        )
