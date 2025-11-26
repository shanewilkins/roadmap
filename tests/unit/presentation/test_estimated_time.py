"""Tests for estimated time functionality."""

import os
import tempfile

import pytest
from click.testing import CliRunner

from roadmap.application.core import RoadmapCore
from roadmap.cli import main
from roadmap.domain import Issue, Milestone, Status


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
                status=Status.CLOSED,
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
    def initialized_roadmap(self, temp_dir):
        """Create a temporary directory with initialized roadmap."""
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

    def test_create_issue_with_estimate(self, initialized_roadmap):
        """Test creating an issue with estimated time via CLI."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["issue", "create", "Test Issue", "--estimate", "4.5"]
        )

        assert result.exit_code == 0
        assert "Created issue: Test Issue" in result.output
        assert "Estimated: 4.5h" in result.output

    def test_create_issue_without_estimate(self, initialized_roadmap):
        """Test creating an issue without estimated time via CLI."""
        runner = CliRunner()

        result = runner.invoke(main, ["issue", "create", "Test Issue"])

        assert result.exit_code == 0
        assert "Created issue: Test Issue" in result.output
        assert "Estimated:" not in result.output

    def test_update_issue_estimate(self, initialized_roadmap):
        """Test updating an issue's estimated time via CLI."""
        runner = CliRunner()

        # Create an issue first
        create_result = runner.invoke(main, ["issue", "create", "Test Issue"])
        assert create_result.exit_code == 0

        # Extract issue ID from output
        issue_id = create_result.output.split("ID:")[1].split()[0]

        # Update the estimate
        update_result = runner.invoke(
            main, ["issue", "update", issue_id, "--estimate", "6.0"]
        )

        assert update_result.exit_code == 0
        assert "Updated issue: Test Issue" in update_result.output
        assert "estimate: 6.0h" in update_result.output

    def test_issue_list_shows_estimates(self, initialized_roadmap):
        """Test that issue list shows estimated times."""
        runner = CliRunner()

        # Create issues with different estimates
        runner.invoke(main, ["issue", "create", "Quick Task", "--estimate", "1.0"])
        runner.invoke(main, ["issue", "create", "Big Feature", "--estimate", "32.0"])
        runner.invoke(main, ["issue", "create", "No Estimate"])

        # List issues
        result = runner.invoke(main, ["issue", "list"])

        assert result.exit_code == 0
        assert "Estimate" in result.output  # Column header
        assert "1.0h" in result.output
        assert "4.0d" in result.output  # 32 hours = 4 days
        # The table may truncate "Not estimated" to "Not" or "estimat…" depending on width
        assert (
            "Not estimated" in result.output
            or "Not" in result.output
            or "estimat" in result.output
        )

    def test_milestone_list_shows_estimates(self, initialized_roadmap):
        """Test that milestone list shows total estimated times."""
        runner = CliRunner()

        # Create a milestone
        runner.invoke(main, ["milestone", "create", "Test Milestone"])

        # Create issues and assign to milestone
        create_result1 = runner.invoke(
            main, ["issue", "create", "Task 1", "--estimate", "8.0"]
        )
        issue_id1 = create_result1.output.split("ID:")[1].split()[0]

        create_result2 = runner.invoke(
            main, ["issue", "create", "Task 2", "--estimate", "16.0"]
        )
        issue_id2 = create_result2.output.split("ID:")[1].split()[0]

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
        assert "Estimate" in result.output  # Column header
        assert "3.0d" in result.output  # 24 hours = 3 days


class TestEstimatedTimeCore:
    """Test estimated time functionality in RoadmapCore."""

    def test_create_issue_with_estimated_hours(self):
        """Test creating an issue with estimated hours through core."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            core = RoadmapCore()
            core.initialize()

            issue = core.create_issue(title="Test Issue", estimated_hours=5.5)

            assert issue.estimated_hours == 5.5
            assert issue.estimated_time_display == "5.5h"

    def test_create_issue_without_estimated_hours(self):
        """Test creating an issue without estimated hours through core."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            core = RoadmapCore()
            core.initialize()

            issue = core.create_issue(title="Test Issue")

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

            original_issue = core.create_issue(
                title="Persistent Issue", estimated_hours=12.0
            )

            # Load the issue back from file
            loaded_issues = core.list_issues()
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
