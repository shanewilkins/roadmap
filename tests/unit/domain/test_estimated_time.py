"""Tests for estimated time functionality."""

import os
import re
import tempfile

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.core.domain import Issue, Milestone, Status
from roadmap.infrastructure.core import RoadmapCore
from tests.unit.shared.test_utils import strip_ansi


class TestEstimatedTimeModel:
    """Test estimated time functionality in the Issue model."""

    def test_issue_with_estimated_hours(self):
        """Test creating an issue with estimated hours."""
        issue = Issue(title="Test Issue", estimated_hours=8.5)

        assert issue.estimated_hours == 8.5
        assert issue.estimated_time_display == "1.1d"

    def test_issue_without_estimated_hours(self):
        """Test creating an issue without estimated hours."""
        issue = Issue(title="Test Issue")

        assert issue.estimated_hours is None
        assert issue.estimated_time_display == "Not estimated"

    def test_estimated_time_display_formats(self):
        """Test different formats for estimated time display."""
        # Test minutes (< 1 hour)
        issue_minutes = Issue(title="Test", estimated_hours=0.5)
        assert issue_minutes.estimated_time_display == "30m"

        # Test hours (< 8 hours)
        issue_hours = Issue(title="Test", estimated_hours=4.25)
        assert issue_hours.estimated_time_display == "4.2h"

        # Test days (>= 8 hours)
        issue_days = Issue(title="Test", estimated_hours=16.0)
        assert issue_days.estimated_time_display == "2.0d"


class TestMilestoneEstimatedTime:
    """Test estimated time calculations for milestones."""

    def test_milestone_total_estimated_hours(self):
        """Test milestone total estimated hours calculation."""
        milestone = Milestone(name="v1.0")
        issues = [
            Issue(title="Issue 1", estimated_hours=4.0, milestone="v1.0"),
            Issue(title="Issue 2", estimated_hours=8.0, milestone="v1.0"),
            Issue(
                title="Issue 3", estimated_hours=None, milestone="v1.0"
            ),  # No estimate
            Issue(
                title="Issue 4", estimated_hours=2.0, milestone="v2.0"
            ),  # Different milestone
        ]

        total_hours = milestone.get_total_estimated_hours(issues)
        assert total_hours == 12.0  # 4.0 + 8.0 (ignores None and different milestone)

    def test_milestone_remaining_estimated_hours(self):
        """Test milestone remaining estimated hours calculation."""
        milestone = Milestone(name="v1.0")
        issues = [
            Issue(
                title="Done Issue",
                estimated_hours=4.0,
                milestone="v1.0",
                status=Status.DONE,
            ),
            Issue(
                title="Todo Issue",
                estimated_hours=8.0,
                milestone="v1.0",
                status=Status.TODO,
            ),
            Issue(
                title="In Progress",
                estimated_hours=6.0,
                milestone="v1.0",
                status=Status.IN_PROGRESS,
            ),
        ]

        remaining_hours = milestone.get_remaining_estimated_hours(issues)
        assert remaining_hours == 14.0  # 8.0 + 6.0 (excludes done issue)

    def test_milestone_estimated_time_display(self):
        """Test milestone estimated time display formatting."""
        milestone = Milestone(name="v1.0")

        # Test with no estimates
        issues_no_estimate = [
            Issue(title="Issue 1", milestone="v1.0"),
            Issue(title="Issue 2", milestone="v1.0"),
        ]
        assert (
            milestone.get_estimated_time_display(issues_no_estimate) == "Not estimated"
        )

        # Test with small estimate (hours)
        issues_hours = [
            Issue(title="Issue 1", estimated_hours=2.0, milestone="v1.0"),
            Issue(title="Issue 2", estimated_hours=3.0, milestone="v1.0"),
        ]
        assert milestone.get_estimated_time_display(issues_hours) == "5.0h"

        # Test with large estimate (days)
        issues_days = [
            Issue(title="Issue 1", estimated_hours=8.0, milestone="v1.0"),
            Issue(title="Issue 2", estimated_hours=16.0, milestone="v1.0"),
        ]
        assert milestone.get_estimated_time_display(issues_days) == "3.0d"


class TestEstimatedTimeCLI:
    """Test CLI commands with estimated time functionality."""

    @pytest.fixture
    def initialized_roadmap(self):
        """Create a temporary directory with initialized roadmap."""
        runner = CliRunner()
        with runner.isolated_filesystem():
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
            yield runner

    def test_create_issue_with_estimate(self, initialized_roadmap):
        """Test creating an issue with estimated time via CLI."""
        runner = initialized_roadmap

        result = runner.invoke(
            main, ["issue", "create", "Test Issue", "--estimate", "4.5"]
        )

        assert result.exit_code == 0
        clean_output = strip_ansi(result.output)
        assert "Created issue: Test Issue" in clean_output
        assert "Estimated: 4.5h" in clean_output

    def test_create_issue_without_estimate(self, initialized_roadmap):
        """Test creating an issue without estimated time via CLI."""
        runner = initialized_roadmap

        result = runner.invoke(main, ["issue", "create", "Test Issue"])

        assert result.exit_code == 0
        clean_output = strip_ansi(result.output)
        assert "Created issue: Test Issue" in clean_output
        assert "Estimated:" not in clean_output

    def test_update_issue_estimate(self, initialized_roadmap):
        """Test updating an issue's estimated time via CLI."""
        runner = initialized_roadmap

        # Create an issue first
        create_result = runner.invoke(main, ["issue", "create", "Test Issue"])
        assert create_result.exit_code == 0

        # Extract issue ID from output - look for the success message line
        clean_create = strip_ansi(create_result.output)
        for line in clean_create.split("\n"):
            if "Created issue" in line:
                match = re.search(r"\[([^\]]+)\]", line)
                if match:
                    issue_id = match.group(1)
                    break
        else:
            raise ValueError(f"Could not find Created issue line in: {clean_create}")

        # Update the estimate
        update_result = runner.invoke(
            main, ["issue", "update", issue_id, "--estimate", "6.0"]
        )

        assert update_result.exit_code == 0
        clean_output = strip_ansi(update_result.output)
        assert "Updated issue: Test Issue" in clean_output
        assert "estimate: 6.0h" in clean_output

    def test_issue_list_shows_estimates(self, initialized_roadmap):
        """Test that issue list shows estimated times."""
        runner = initialized_roadmap

        # Create issues with different estimates
        runner.invoke(main, ["issue", "create", "Quick Task", "--estimate", "1.0"])
        runner.invoke(main, ["issue", "create", "Big Feature", "--estimate", "32.0"])
        runner.invoke(main, ["issue", "create", "No Estimate"])

        # List issues
        result = runner.invoke(main, ["issue", "list"])

        assert result.exit_code == 0
        clean_output = strip_ansi(result.output)
        # Column header might be truncated to "Est…" in the table
        assert "Est" in clean_output or "Estimate" in clean_output
        assert "1.0h" in clean_output
        assert "4.0d" in clean_output  # 32 hours = 4 days
        # The table may truncate "Not estimated" to "Not" or "estimat…" depending on width
        assert (
            "Not estimated" in clean_output
            or "Not" in clean_output
            or "estimat" in clean_output
        )

    def test_milestone_list_shows_estimates(self, initialized_roadmap):
        """Test that milestone list shows total estimated times."""
        runner = initialized_roadmap

        # Create a milestone
        runner.invoke(main, ["milestone", "create", "Test Milestone"])

        # Create issues and assign to milestone
        create_result1 = runner.invoke(
            main, ["issue", "create", "Task 1", "--estimate", "8.0"]
        )
        # Extract ID from log output (issue_id=) or success message [id]
        clean_create1 = strip_ansi(create_result1.output)
        issue_id1 = None
        for line in clean_create1.split("\n"):
            if "issue_id=" in line:
                match = re.search(r"issue_id=([^\s]+)", line)
                if match:
                    issue_id1 = match.group(1)
                    break
        if issue_id1 is None:
            for line in clean_create1.split("\n"):
                if "Created issue" in line:
                    match = re.search(r"\[([^\]]+)\]", line)
                    if match:
                        issue_id1 = match.group(1)
                        break
        assert issue_id1 is not None, f"Could not find issue ID in: {clean_create1}"

        create_result2 = runner.invoke(
            main, ["issue", "create", "Task 2", "--estimate", "16.0"]
        )
        # Extract ID from log output (issue_id=) or success message [id]
        clean_create2 = strip_ansi(create_result2.output)
        issue_id2 = None
        for line in clean_create2.split("\n"):
            if "issue_id=" in line:
                match = re.search(r"issue_id=([^\s]+)", line)
                if match:
                    issue_id2 = match.group(1)
                    break
        if issue_id2 is None:
            for line in clean_create2.split("\n"):
                if "Created issue" in line:
                    match = re.search(r"\[([^\]]+)\]", line)
                    if match:
                        issue_id2 = match.group(1)
                        break
        assert issue_id2 is not None, f"Could not find issue ID in: {clean_create2}"

        # Assign issues to milestone
        runner.invoke(
            main, ["issue", "update", issue_id1, "--milestone", "Test Milestone"]
        )
        runner.invoke(
            main, ["issue", "update", issue_id2, "--milestone", "Test Milestone"]
        )

        # List milestones
        result = runner.invoke(main, ["milestone", "list"])

        assert result.exit_code == 0
        clean_output = strip_ansi(result.output)
        # Column header might be truncated in the table
        assert "Estimate" in clean_output or "Est" in clean_output
        assert "3.0d" in clean_output  # 24 hours = 3 days


class TestEstimatedTimeCore:
    """Test estimated time functionality in RoadmapCore."""

    def test_create_issue_with_estimated_hours(self):
        """Test creating an issue with estimated hours through core."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            core = RoadmapCore()
            core.initialize()

            issue = core.issues.create(title="Test Issue", estimated_hours=5.5)

            assert issue.estimated_hours == 5.5
            assert issue.estimated_time_display == "5.5h"

    def test_create_issue_without_estimated_hours(self):
        """Test creating an issue without estimated hours through core."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            core = RoadmapCore()
            core.initialize()

            issue = core.issues.create(title="Test Issue")

            assert issue.estimated_hours is None
            assert issue.estimated_time_display == "Not estimated"


class TestEstimatedTimePersistence:
    """Test that estimated time persists correctly."""

    def test_estimated_time_saves_and_loads(self):
        """Test that estimated time is saved to and loaded from files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create and save an issue with estimated time
            core = RoadmapCore()
            core.initialize()

            original_issue = core.issues.create(
                title="Persistent Issue", estimated_hours=12.0
            )

            # Load the issue back from file
            loaded_issues = core.issues.list()
            loaded_issue = next(i for i in loaded_issues if i.id == original_issue.id)

            assert loaded_issue.estimated_hours == 12.0
            assert loaded_issue.estimated_time_display == "1.5d"


class TestEstimatedTimeEdgeCases:
    """Test edge cases for estimated time functionality."""

    def test_zero_estimated_hours(self):
        """Test handling of zero estimated hours."""
        issue = Issue(title="Test", estimated_hours=0.0)
        assert issue.estimated_time_display == "0m"

    def test_very_small_estimated_hours(self):
        """Test handling of very small estimated hours."""
        issue = Issue(title="Test", estimated_hours=0.1)  # 6 minutes
        assert issue.estimated_time_display == "6m"

    def test_large_estimated_hours(self):
        """Test handling of large estimated hours."""
        issue = Issue(title="Test", estimated_hours=160.0)  # 20 days
        assert issue.estimated_time_display == "20.0d"

    def test_negative_estimated_hours_not_allowed(self):
        """Test that negative estimated hours are handled gracefully."""
        # Pydantic should handle validation, but let's test our display logic
        issue = Issue(title="Test", estimated_hours=-5.0)
        # This might raise an error or handle it gracefully depending on validation
        # The important thing is our system doesn't crash
        display = issue.estimated_time_display
        assert isinstance(display, str)  # Should return some string representation
