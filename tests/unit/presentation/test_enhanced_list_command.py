"""Tests for enhanced list command functionality."""

import os
import tempfile
from datetime import UTC, datetime, timedelta

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.core.domain import Milestone, MilestoneStatus, Priority, Status
from roadmap.infrastructure.coordination.core import RoadmapCore
from tests.fixtures.cli_test_helpers import CLIOutputParser


@pytest.fixture
def temp_roadmap(temp_dir_context):
    """Create a temporary roadmap for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        old_cwd = os.getcwd()
        os.chdir(temp_dir)
        try:
            core = RoadmapCore()
            core.initialize()

            issue1 = core.issues.create("Open Todo Issue", priority=Priority.HIGH)
            issue2 = core.issues.create("Blocked Issue", priority=Priority.MEDIUM)
            issue3 = core.issues.create("Done Issue", priority=Priority.LOW)
            core.issues.create("Backlog Issue", priority=Priority.CRITICAL)

            core.issues.update(issue2.id, status=Status.BLOCKED)
            core.issues.update(issue3.id, status=Status.CLOSED)

            core.milestones.create("Test Sprint", "Test sprint description")
            core.move_issue_to_milestone(issue1.id, "Test Sprint")
            core.move_issue_to_milestone(issue2.id, "Test Sprint")
            core.move_issue_to_milestone(issue3.id, "Test Sprint")

            future_date = datetime.now(UTC) + timedelta(days=30)
            future_milestone = Milestone(
                name="Future Sprint",
                headline="Future sprint",
                due_date=future_date,
                status=MilestoneStatus.OPEN,
            )
            milestone_path = core.milestones_dir / future_milestone.filename
            MilestoneParser.save_milestone_file(future_milestone, milestone_path)

            issue5 = core.issues.create("Future Issue", priority=Priority.HIGH)
            core.move_issue_to_milestone(issue5.id, "Future Sprint")

            yield core
        finally:
            os.chdir(old_cwd)


class TestListAllVariants:
    """Test list command with various filters."""

    @staticmethod
    def _extract_titles_and_statuses(
        output: str,
    ) -> tuple[list[str], list[str], list[list]]:
        data = CLIOutputParser.extract_json(output)
        assert isinstance(data, dict)
        columns = data.get("columns", [])
        rows = data.get("rows", [])

        title_idx = next(i for i, c in enumerate(columns) if c.get("name") == "title")
        status_idx = next(i for i, c in enumerate(columns) if c.get("name") == "status")

        titles = [str(row[title_idx]) for row in rows if title_idx < len(row)]
        statuses = [str(row[status_idx]) for row in rows if status_idx < len(row)]
        return titles, statuses, rows

    def test_list_all_issues_exit_code(self, temp_roadmap):
        """Test listing all issues returns success."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list"])
        assert result.exit_code == 0

    def test_list_all_issues_count(self, temp_roadmap):
        """Test listing all issues shows correct count."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list"])
        assert "5 all issues" in result.output

    def test_list_all_issues_contains_statuses(self, temp_roadmap):
        """Test listing all issues includes all status categories."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list", "--format", "json"])
        assert result.exit_code == 0
        _, statuses, _ = self._extract_titles_and_statuses(result.output)
        assert "todo" in statuses
        assert "blocked" in statuses
        assert "closed" in statuses

    def test_list_all_issues_contains_backlog_and_future(self, temp_roadmap):
        """Test listing all issues includes backlog and future categories."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list", "--format", "json"])
        assert result.exit_code == 0
        titles, _, _ = self._extract_titles_and_statuses(result.output)
        assert "Backlog Issue" in titles
        assert "Future Issue" in titles

    @pytest.mark.parametrize(
        "filter_flag,expected_count,should_contain,should_not_contain",
        [
            (
                "--open",
                "4",
                ["Open Todo Issue", "Blocked Issue", "Backlog Issue", "Future Issue"],
                ["Done Issue"],
            ),
            ("--blocked", "1", ["Blocked Issue"], ["Open Todo Issue", "Done Issue"]),
            ("--backlog", "1", ["Backlog Issue"], ["Open Todo Issue"]),
        ],
    )
    def test_list_with_status_filters(
        self,
        temp_roadmap,
        filter_flag,
        expected_count,
        should_contain,
        should_not_contain,
    ):
        """Test listing with various status filters."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list", filter_flag, "--format", "json"])
        assert result.exit_code == 0
        titles, _, rows = self._extract_titles_and_statuses(result.output)
        assert len(rows) == int(expected_count)
        for text in should_contain:
            assert text in titles
        for text in should_not_contain:
            assert text not in titles

    def test_list_unassigned_alias(self, temp_roadmap, strip_ansi_fixture):
        """Test that --unassigned is an alias for --backlog."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list", "--unassigned"])
        assert result.exit_code == 0
        clean_output = strip_ansi_fixture(result.output)
        assert "1 backlog issue" in clean_output
        assert "Issue" in clean_output

    def test_list_milestone_issues(self, temp_roadmap, strip_ansi_fixture):
        """Test listing issues for a specific milestone."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["issue", "list", "--milestone", "Test Sprint", "--format", "json"],
        )
        assert result.exit_code == 0
        titles, _, rows = self._extract_titles_and_statuses(result.output)
        assert len(rows) == 3
        assert "Open Todo Issue" in titles
        assert "Blocked Issue" in titles
        assert "Done Issue" in titles
        assert "Backlog Issue" not in titles

    def test_list_next_milestone_issues(self, temp_roadmap, strip_ansi_fixture):
        """Test listing issues for the next upcoming milestone."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["issue", "list", "--next-milestone", "--format", "json"],
        )
        assert result.exit_code == 0
        titles, _, rows = self._extract_titles_and_statuses(result.output)
        assert len(rows) == 1
        assert "Future Issue" in titles
        assert "Open Todo Issue" not in titles

    def test_list_combined_filters(self, temp_roadmap, strip_ansi_fixture):
        """Test combining compatible filters."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["issue", "list", "--open", "--priority", "high", "--format", "json"],
        )
        assert result.exit_code == 0
        titles, _, rows = self._extract_titles_and_statuses(result.output)
        assert len(rows) == 2
        assert "Open Todo Issue" in titles
        assert "Future Issue" in titles

    def test_conflicting_filters_error(self, temp_roadmap):
        """Test that conflicting filters show an error."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["issue", "list", "--backlog", "--milestone", "Test Sprint"]
        )
        assert result.exit_code == 0
        assert (
            "Cannot combine --backlog, --unassigned, --next-milestone" in result.output
        )
        assert "and --milestone" in result.output

    def test_empty_filter_results(self, temp_roadmap):
        """Test filters that return no results."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list", "--status", "review"])
        assert result.exit_code == 0
        assert "No all review issues found" in result.output
        assert "Create one with" in result.output

    @pytest.mark.parametrize(
        "args,expected_desc",
        [
            (["--open"], "all open"),
            (["--blocked"], "all blocked"),
            (["--backlog"], "backlog"),
            (["--open", "--priority", "high"], "all open high priority"),
            (["--milestone", "Test Sprint"], "milestone 'test sprint'"),
        ],
    )
    def test_header_descriptions(self, temp_roadmap, args, expected_desc):
        """Test that filter descriptions are shown correctly in headers."""
        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list"] + args)
        assert result.exit_code == 0
        assert expected_desc in result.output.lower()


class TestNextMilestoneLogic:
    """Test next milestone logic and edge cases."""

    def test_next_milestone_no_due_dates(self, temp_roadmap):
        """Test next milestone when no milestones have due dates."""
        future_milestone_path = temp_roadmap.milestones_dir / "future-sprint.md"
        if future_milestone_path.exists():
            future_milestone_path.unlink()

        runner = CliRunner()
        result = runner.invoke(main, ["issue", "list", "--next-milestone"])
        assert result.exit_code == 0
        assert "No upcoming milestones with due dates found" in result.output

    def test_get_next_milestone_method(self, temp_roadmap):
        """Test the get_next_milestone core method."""
        next_milestone = temp_roadmap.get_next_milestone()
        assert next_milestone is not None
        assert next_milestone.name == "Future Sprint"
        assert next_milestone.due_date is not None
