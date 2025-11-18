"""Tests for enhanced list command functionality."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner

from roadmap.presentation.cli import main
from roadmap.application.core import RoadmapCore
from roadmap.domain import Milestone, MilestoneStatus, Priority, Status


@pytest.fixture
def temp_roadmap():
    """Create a temporary roadmap for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Change to temp directory
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            # Create test issues
            issue1 = core.create_issue("Open Todo Issue", priority=Priority.HIGH)
            issue2 = core.create_issue("Blocked Issue", priority=Priority.MEDIUM)
            issue3 = core.create_issue("Done Issue", priority=Priority.LOW)
            core.create_issue(
                "Backlog Issue", priority=Priority.CRITICAL
            )  # No milestone

            # Update statuses after creation
            core.update_issue(issue2.id, status=Status.BLOCKED)
            core.update_issue(issue3.id, status=Status.DONE)

            # Create test milestone and assign issues
            core.create_milestone("Test Sprint", "Test sprint description")
            core.move_issue_to_milestone(issue1.id, "Test Sprint")
            core.move_issue_to_milestone(issue2.id, "Test Sprint")
            core.move_issue_to_milestone(issue3.id, "Test Sprint")

            # Create milestone with due date for next milestone testing
            future_date = datetime.now() + timedelta(days=30)
            future_milestone = Milestone(
                name="Future Sprint",
                description="Future sprint",
                due_date=future_date,
                status=MilestoneStatus.OPEN,
            )
            milestone_path = core.milestones_dir / future_milestone.filename
            from roadmap.parser import MilestoneParser

            MilestoneParser.save_milestone_file(future_milestone, milestone_path)

            # Create issue for future milestone
            issue5 = core.create_issue("Future Issue", priority=Priority.HIGH)
            core.move_issue_to_milestone(issue5.id, "Future Sprint")

            yield core
        finally:
            os.chdir(old_cwd)


def test_list_all_issues(temp_roadmap):
    """Test listing all issues with all priority levels and types."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list"])

    assert result.exit_code == 0
    assert "5 all issues" in result.output
    # Check for actual issue titles in the output
    assert "Todo" in result.output  # "Open Todo Issue"
    assert "Blocked" in result.output  # "Blocked Issue"
    assert "Done" in result.output  # "Done Issue"
    assert "Backlog" in result.output  # "Backlog Issue"
    assert "Future" in result.output  # "Future Issue"


def test_list_open_issues(temp_roadmap, strip_ansi_fixture):
    """Test listing only open (not done) issues."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--open"])

    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "4 all open issues" in clean_output
    assert "Open Todo Issue" in clean_output
    assert "Blocked Issue" in clean_output
    assert "Backlog Issue" in clean_output
    assert "Future Issue" in clean_output
    assert "Done Issue" not in clean_output


def test_list_blocked_issues(temp_roadmap, strip_ansi_fixture):
    """Test listing only blocked issues."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--blocked"])

    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "1 all blocked issue" in clean_output
    assert "Blocked Issue" in clean_output
    assert "Open Todo Issue" not in clean_output
    assert "Done Issue" not in clean_output


def test_list_backlog_issues(temp_roadmap, strip_ansi_fixture):
    """Test listing only backlog issues."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--backlog"])

    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "1 backlog issue" in clean_output
    assert "Backlog Issue" in clean_output
    assert "Open Todo Issue" not in clean_output


def test_list_unassigned_issues(temp_roadmap, strip_ansi_fixture):
    """Test that --unassigned is an alias for --backlog."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--unassigned"])

    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "1 backlog issue" in clean_output
    assert "Backlog Issue" in clean_output


def test_list_milestone_issues(temp_roadmap, strip_ansi_fixture):
    """Test listing issues for a specific milestone."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--milestone", "Test Sprint"])

    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "3 milestone 'Test Sprint' issues" in clean_output
    assert "Open Todo Issue" in clean_output
    assert "Blocked Issue" in clean_output
    assert "Done Issue" in clean_output
    assert "Backlog Issue" not in clean_output


def test_list_next_milestone_issues(temp_roadmap, strip_ansi_fixture):
    """Test listing issues for the next upcoming milestone."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--next-milestone"])

    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "next milestone (Future Sprint)" in clean_output
    assert "Future Issue" in clean_output
    assert "Open Todo Issue" not in clean_output


def test_list_combined_filters(temp_roadmap, strip_ansi_fixture):
    """Test combining compatible filters."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--open", "--priority", "high"])

    assert result.exit_code == 0
    clean_output = strip_ansi_fixture(result.output)
    assert "all open high priority" in clean_output
    assert "Open Todo Issue" in clean_output
    assert "Future Issue" in clean_output
    assert "Blocked Issue" not in result.output  # medium priority
    assert "Done Issue" not in result.output  # not open


def test_conflicting_filters_error(temp_roadmap):
    """Test that conflicting filters show an error."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["issue", "list", "--backlog", "--milestone", "Test Sprint"]
    )

    assert result.exit_code == 0
    # Handle line breaks in error message
    assert "Cannot combine --backlog, --unassigned, --next-milestone" in result.output
    assert "and --milestone" in result.output and "filters" in result.output


def test_next_milestone_no_due_dates(temp_roadmap):
    """Test next milestone when no milestones have due dates."""
    # Remove the future milestone
    future_milestone_path = temp_roadmap.milestones_dir / "future-sprint.md"
    if future_milestone_path.exists():
        future_milestone_path.unlink()

    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--next-milestone"])

    assert result.exit_code == 0
    assert "No upcoming milestones with due dates found" in result.output


def test_get_next_milestone_method(temp_roadmap):
    """Test the get_next_milestone core method."""
    next_milestone = temp_roadmap.get_next_milestone()

    assert next_milestone is not None
    assert next_milestone.name == "Future Sprint"
    assert next_milestone.due_date is not None


def test_empty_filter_results(temp_roadmap):
    """Test filters that return no results."""
    runner = CliRunner()
    result = runner.invoke(main, ["issue", "list", "--status", "review"])

    assert result.exit_code == 0
    assert "No all review issues found" in result.output
    assert "Create one with" in result.output


def test_header_descriptions(temp_roadmap):
    """Test that filter descriptions are shown correctly in headers."""
    runner = CliRunner()

    # Test various filter combinations
    test_cases = [
        (["--open"], "all open"),
        (["--blocked"], "all blocked"),
        (["--backlog"], "backlog"),
        (["--open", "--priority", "high"], "all open high priority"),
        (["--milestone", "Test Sprint"], "milestone 'test sprint'"),  # lowercased
    ]

    for args, expected_desc in test_cases:
        result = runner.invoke(main, ["issue", "list"] + args)
        assert result.exit_code == 0
        assert expected_desc in result.output.lower()
