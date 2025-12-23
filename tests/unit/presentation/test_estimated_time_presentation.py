"""Tests for estimated time presentation - tests Rich formatting without CLI output parsing."""

from roadmap.core.domain import Issue, Milestone, Status


class TestEstimatedTimePresentation:
    """Test estimated time display formatting."""

    def test_issue_estimated_time_display_formats(self):
        """Test different estimated time display formats."""
        test_cases = [
            (0.5, "30m"),  # Minutes (< 1 hour)
            (1.0, "1.0h"),  # 1 hour
            (2.0, "2.0h"),  # Multiple hours
            (4.25, "4.2h"),  # Hours with decimals
            (7.75, "7.8h"),  # Just under 8 hours
            (8.0, "1.0d"),  # Exactly 1 day
            (16.0, "2.0d"),  # Multiple days
            (32.0, "4.0d"),  # Large estimate
            (None, "Not estimated"),  # No estimate
        ]

        for hours, expected_display in test_cases:
            issue = Issue(title="Test", estimated_hours=hours)
            assert (
                issue.estimated_time_display == expected_display
            ), f"Estimated hours {hours} should display as '{expected_display}', got '{issue.estimated_time_display}'"

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
        assert total_hours == 12.0  # 4.0 + 8.0 (excludes None and different milestone)

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
        assert remaining_hours == 14.0  # 8.0 + 6.0 (excludes closed issue)

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
