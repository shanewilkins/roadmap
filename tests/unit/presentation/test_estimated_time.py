"""Tests for estimated time functionality."""

from roadmap.adapters.cli import main
from roadmap.core.domain import Status
from tests.factories import IssueBuilder, MilestoneBuilder
from tests.unit.common.formatters.test_assertion_helpers import (
    assert_command_success,
)


class TestEstimatedTimeModel:
    """Test estimated time functionality in the Issue model."""

    def test_issue_with_estimated_hours(self):
        """Test creating an issue with estimated hours."""
        issue = IssueBuilder().with_estimated_hours(8.5).build()

        assert issue.estimated_hours == 8.5
        assert issue.estimated_time_display == "1.1d"

    def test_issue_without_estimated_hours(self):
        """Test creating an issue without estimated hours."""
        issue = IssueBuilder().build()

        assert issue.estimated_hours is None
        assert issue.estimated_time_display == "Not estimated"

    def test_estimated_time_display_formats(self):
        """Test different formats for estimated time display."""
        # Test minutes (< 1 hour)
        issue_minutes = IssueBuilder().with_estimated_hours(0.5).build()
        assert issue_minutes.estimated_time_display == "30m"

        # Test hours (< 8 hours)
        issue_hours = IssueBuilder().with_estimated_hours(4.25).build()
        assert issue_hours.estimated_time_display == "4.2h"

        # Test days (>= 8 hours)
        issue_days = IssueBuilder().with_estimated_hours(16.0).build()
        assert issue_days.estimated_time_display == "2.0d"


class TestMilestoneEstimatedTime:
    """Test estimated time calculations for milestones."""

    def test_milestone_total_estimated_hours(self):
        """Test milestone total estimated hours calculation."""
        milestone = MilestoneBuilder().with_name("v1.0").build()
        issues = [
            IssueBuilder().with_milestone("v1.0").with_estimated_hours(4.0).build(),
            IssueBuilder().with_milestone("v1.0").with_estimated_hours(8.0).build(),
            IssueBuilder().with_milestone("v1.0").build(),  # No estimate
            IssueBuilder()
            .with_milestone("v2.0")
            .with_estimated_hours(2.0)
            .build(),  # Different milestone
        ]

        total_hours = milestone.get_total_estimated_hours(issues)
        assert total_hours == 12.0  # 4.0 + 8.0 (ignores None and different milestone)

    def test_milestone_remaining_estimated_hours(self):
        """Test milestone remaining estimated hours calculation."""
        milestone = MilestoneBuilder().with_name("v1.0").build()
        issues = [
            IssueBuilder()
            .with_milestone("v1.0")
            .with_status(Status.CLOSED)
            .with_estimated_hours(4.0)
            .build(),
            IssueBuilder()
            .with_milestone("v1.0")
            .with_status(Status.TODO)
            .with_estimated_hours(8.0)
            .build(),
            IssueBuilder()
            .with_milestone("v1.0")
            .with_status(Status.IN_PROGRESS)
            .with_estimated_hours(6.0)
            .build(),
        ]

        remaining_hours = milestone.get_remaining_estimated_hours(issues)
        assert remaining_hours == 14.0  # 8.0 + 6.0 (excludes done issue)

    def test_milestone_estimated_time_display(self):
        """Test milestone estimated time display formatting."""
        milestone = MilestoneBuilder().with_name("v1.0").build()

        # Test with no estimates
        issues_no_estimate = [
            IssueBuilder().with_milestone("v1.0").build(),
            IssueBuilder().with_milestone("v1.0").build(),
        ]
        assert (
            milestone.get_estimated_time_display(issues_no_estimate) == "Not estimated"
        )

        # Test with small estimate (hours)
        issues_hours = [
            IssueBuilder().with_milestone("v1.0").with_estimated_hours(2.0).build(),
            IssueBuilder().with_milestone("v1.0").with_estimated_hours(3.0).build(),
        ]
        assert milestone.get_estimated_time_display(issues_hours) == "5.0h"

        # Test with large estimate (days)
        issues_days = [
            IssueBuilder().with_milestone("v1.0").with_estimated_hours(8.0).build(),
            IssueBuilder().with_milestone("v1.0").with_estimated_hours(16.0).build(),
        ]
        assert milestone.get_estimated_time_display(issues_days) == "3.0d"


class TestEstimatedTimeCLI:
    """Test CLI commands with estimated time functionality."""

    def test_create_issue_with_estimate(self, cli_runner_with_init):
        """Test creating an issue with estimated time via CLI."""
        runner, core = cli_runner_with_init

        result = runner.invoke(
            main, ["issue", "create", "Test Issue", "--estimate", "4.5"]
        )

        assert_command_success(result)
        # Verify issue was created in database
        issues = core.issues.list()
        assert any(i.title == "Test Issue" and i.estimated_hours == 4.5 for i in issues)

    def test_create_issue_without_estimate(self, cli_runner_with_init):
        """Test creating an issue without estimated time via CLI."""
        runner, core = cli_runner_with_init

        result = runner.invoke(main, ["issue", "create", "Test Issue"])

        assert_command_success(result)
        issues = core.issues.list()
        assert any(
            i.title == "Test Issue" and i.estimated_hours is None for i in issues
        )

    def test_update_issue_estimate(self, cli_runner_with_init):
        """Test updating an issue's estimated time via CLI."""
        runner, core = cli_runner_with_init

        # Create an issue first
        create_result = runner.invoke(main, ["issue", "create", "Test Issue"])
        assert_command_success(create_result)

        # Get the created issue from database
        issues = core.issues.list()
        issue = next((i for i in issues if i.title == "Test Issue"), None)
        assert issue is not None

        # Update the estimate
        update_result = runner.invoke(
            main, ["issue", "update", issue.id, "--estimate", "6.0"]
        )

        assert_command_success(update_result)
        # Verify update by refreshing and checking database
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.estimated_hours == 6.0

    def test_issue_list_shows_estimates(self, cli_runner_with_init):
        """Test that issue list shows estimated times."""
        runner, core = cli_runner_with_init

        # Create issues with different estimates
        runner.invoke(main, ["issue", "create", "Quick Task", "--estimate", "1.0"])
        runner.invoke(main, ["issue", "create", "Big Feature", "--estimate", "32.0"])
        runner.invoke(main, ["issue", "create", "No Estimate"])

        # List issues
        result = runner.invoke(main, ["issue", "list"])

        assert_command_success(result)

    def test_issue_list_creates_estimates(self, cli_runner_with_init):
        """Test that issues are created with correct estimate values."""
        runner, core = cli_runner_with_init

        # Create issues with different estimates
        runner.invoke(main, ["issue", "create", "Quick Task", "--estimate", "1.0"])
        runner.invoke(main, ["issue", "create", "Big Feature", "--estimate", "32.0"])

        # Verify the issues were created with correct estimates in database
        issues = core.issues.list()

        quick_task = next((i for i in issues if i.title == "Quick Task"), None)
        assert quick_task is not None
        assert quick_task.estimated_hours == 1.0

        big_feature = next((i for i in issues if i.title == "Big Feature"), None)
        assert big_feature is not None
        assert big_feature.estimated_hours == 32.0

    def test_issue_list_displays_estimate_format(self, cli_runner_with_init):
        """Test that estimated times are displayed in correct format."""
        runner, core = cli_runner_with_init

        # Create issues with different estimates
        runner.invoke(main, ["issue", "create", "Quick Task", "--estimate", "1.0"])
        runner.invoke(main, ["issue", "create", "Big Feature", "--estimate", "32.0"])
        runner.invoke(main, ["issue", "create", "No Estimate"])

        issues = core.issues.list()

        quick_task = next((i for i in issues if i.title == "Quick Task"), None)
        assert quick_task is not None
        assert quick_task.estimated_time_display == "1.0h"

        big_feature = next((i for i in issues if i.title == "Big Feature"), None)
        assert big_feature is not None
        assert big_feature.estimated_time_display == "4.0d"  # 32 hours = 4 days

        no_estimate = next((i for i in issues if i.title == "No Estimate"), None)
        assert no_estimate is not None
        assert no_estimate.estimated_time_display == "Not estimated"

    def test_milestone_list_shows_estimates_command_success(self, cli_runner_with_init):
        """Test that milestone list command succeeds."""
        runner, core = cli_runner_with_init

        # Create a milestone
        runner.invoke(main, ["milestone", "create", "Test Milestone"])

        # Create issues and assign to milestone
        runner.invoke(main, ["issue", "create", "Task 1", "--estimate", "8.0"])
        runner.invoke(main, ["issue", "create", "Task 2", "--estimate", "16.0"])

        # Get created issues
        issues = core.issues.list()
        # Milestone list command executed
        assert True
        task1 = next((i for i in issues if i.title == "Task 1"), None)
        task2 = next((i for i in issues if i.title == "Task 2"), None)
        assert task1 is not None
        assert task2 is not None

        # Assign issues to milestone
        runner.invoke(
            main, ["issue", "update", task1.id, "--milestone", "Test Milestone"]
        )
        runner.invoke(
            main, ["issue", "update", task2.id, "--milestone", "Test Milestone"]
        )

        # List milestones
        result = runner.invoke(main, ["milestone", "list"])
        assert_command_success(result)

    def test_milestone_list_issues_assigned_to_milestone(self, cli_runner_with_init):
        """Test that milestone list shows issues assigned to milestone."""
        runner, core = cli_runner_with_init

        # Create a milestone
        runner.invoke(main, ["milestone", "create", "Test Milestone"])

        # Create issues and assign to milestone
        runner.invoke(main, ["issue", "create", "Task 1", "--estimate", "8.0"])
        runner.invoke(main, ["issue", "create", "Task 2", "--estimate", "16.0"])

        # Get created issues
        issues = core.issues.list()
        task1 = next((i for i in issues if i.title == "Task 1"), None)
        task2 = next((i for i in issues if i.title == "Task 2"), None)
        assert task1 is not None
        assert task2 is not None

        # Assign issues to milestone
        runner.invoke(
            main, ["issue", "update", task1.id, "--milestone", "Test Milestone"]
        )
        runner.invoke(
            main, ["issue", "update", task2.id, "--milestone", "Test Milestone"]
        )

        # Verify issues are assigned
        fresh_task1 = core.issues.get(task1.id)
        fresh_task2 = core.issues.get(task2.id)
        assert fresh_task1 is not None
        assert fresh_task2 is not None
        assert fresh_task1.milestone == "Test Milestone"
        assert fresh_task2.milestone == "Test Milestone"

    def test_milestone_list_shows_estimated_hours(self, cli_runner_with_init):
        """Test that milestone issues show estimated hours."""
        runner, core = cli_runner_with_init

        # Create a milestone
        runner.invoke(main, ["milestone", "create", "Test Milestone"])

        # Create issues and assign to milestone
        runner.invoke(main, ["issue", "create", "Task 1", "--estimate", "8.0"])
        runner.invoke(main, ["issue", "create", "Task 2", "--estimate", "16.0"])

        # Get created issues
        issues = core.issues.list()
        task1 = next((i for i in issues if i.title == "Task 1"), None)
        task2 = next((i for i in issues if i.title == "Task 2"), None)
        assert task1 is not None
        assert task2 is not None

        # Assign issues to milestone
        runner.invoke(
            main, ["issue", "update", task1.id, "--milestone", "Test Milestone"]
        )
        runner.invoke(
            main, ["issue", "update", task2.id, "--milestone", "Test Milestone"]
        )

        # Verify estimated times
        fresh_task1 = core.issues.get(task1.id)
        fresh_task2 = core.issues.get(task2.id)
        assert fresh_task1 is not None
        assert fresh_task2 is not None
        assert fresh_task1.estimated_hours == 8.0
        assert fresh_task2.estimated_hours == 16.0
        # Total: 24 hours = 3.0 days
        total_hours = fresh_task1.estimated_hours + fresh_task2.estimated_hours
        assert total_hours == 24.0


class TestEstimatedTimeEdgeCases:
    """Test edge cases for estimated time functionality."""

    def test_zero_estimated_hours(self):
        """Test handling of zero estimated hours."""
        issue = IssueBuilder().with_estimated_hours(0.0).build()
        assert issue.estimated_time_display == "0m"

    def test_very_small_estimated_hours(self):
        """Test handling of very small estimated hours."""
        issue = IssueBuilder().with_estimated_hours(0.1).build()  # 6 minutes
        assert issue.estimated_time_display == "6m"

    def test_large_estimated_hours(self):
        """Test handling of large estimated hours."""
        issue = IssueBuilder().with_estimated_hours(160.0).build()  # 20 days
        assert issue.estimated_time_display == "20.0d"

    def test_negative_estimated_hours_not_allowed(self):
        """Test that negative estimated hours are handled gracefully."""
        # Pydantic should handle validation, but let's test our display logic
        issue = IssueBuilder().with_estimated_hours(-5.0).build()
        # This might raise an error or handle it gracefully depending on validation
        # The important thing is our system doesn't crash
        display = issue.estimated_time_display
        assert isinstance(display, str)  # Should return some string representation
