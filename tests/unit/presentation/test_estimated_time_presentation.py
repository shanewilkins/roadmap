"""Tests for estimated time presentation - tests Rich formatting without CLI output parsing."""

import pytest

from roadmap.core.domain import Status
from tests.factories import IssueBuilder, MilestoneBuilder


class TestEstimatedTimePresentation:
    """Test estimated time display formatting."""

    @pytest.mark.parametrize(
        "hours,expected_display",
        [
            (0.5, "30m"),  # Minutes (< 1 hour)
            (1.0, "1.0h"),  # 1 hour
            (2.0, "2.0h"),  # Multiple hours
            (4.25, "4.2h"),  # Hours with decimals
            (7.75, "7.8h"),  # Just under 8 hours
            (8.0, "1.0d"),  # Exactly 1 day
            (16.0, "2.0d"),  # Multiple days
            (32.0, "4.0d"),  # Large estimate
            (None, "Not estimated"),  # No estimate
        ],
    )
    def test_issue_estimated_time_display_formats(self, hours, expected_display):
        """Test different estimated time display formats."""
        issue = IssueBuilder().with_title("Test").with_estimated_hours(hours).build()
        assert issue.estimated_time_display == expected_display

    def test_milestone_total_estimated_hours(self):
        """Test milestone total estimated hours calculation."""
        milestone = MilestoneBuilder().with_name("v1-0").build()
        issues = [
            IssueBuilder()
            .with_title("Issue 1")
            .with_estimated_hours(4.0)
            .with_milestone("v1-0")
            .build(),
            IssueBuilder()
            .with_title("Issue 2")
            .with_estimated_hours(8.0)
            .with_milestone("v1-0")
            .build(),
            IssueBuilder()
            .with_title("Issue 3")
            .with_estimated_hours(None)
            .with_milestone("v1-0")
            .build(),
            IssueBuilder()
            .with_title("Issue 4")
            .with_estimated_hours(2.0)
            .with_milestone("v2-0")
            .build(),
        ]

        total_hours = milestone.get_total_estimated_hours(issues)
        assert total_hours == 12.0

    def test_milestone_remaining_estimated_hours(self):
        """Test milestone remaining estimated hours calculation."""
        milestone = MilestoneBuilder().with_name("v1-0").build()
        issues = [
            IssueBuilder()
            .with_title("Done Issue")
            .with_estimated_hours(4.0)
            .with_milestone("v1-0")
            .with_status(Status.CLOSED)
            .build(),
            IssueBuilder()
            .with_title("Todo Issue")
            .with_estimated_hours(8.0)
            .with_milestone("v1-0")
            .with_status(Status.TODO)
            .build(),
            IssueBuilder()
            .with_title("In Progress")
            .with_estimated_hours(6.0)
            .with_milestone("v1-0")
            .with_status(Status.IN_PROGRESS)
            .build(),
        ]

        remaining_hours = milestone.get_remaining_estimated_hours(issues)
        assert remaining_hours == 14.0

    @pytest.mark.parametrize(
        "issues,expected_display",
        [
            (
                [
                    IssueBuilder().with_title("Issue 1").with_milestone("v1-0").build(),
                    IssueBuilder().with_title("Issue 2").with_milestone("v1-0").build(),
                ],
                "Not estimated",
            ),
            (
                [
                    IssueBuilder()
                    .with_title("Issue 1")
                    .with_estimated_hours(2.0)
                    .with_milestone("v1-0")
                    .build(),
                    IssueBuilder()
                    .with_title("Issue 2")
                    .with_estimated_hours(3.0)
                    .with_milestone("v1-0")
                    .build(),
                ],
                "5.0h",
            ),
            (
                [
                    IssueBuilder()
                    .with_title("Issue 1")
                    .with_estimated_hours(8.0)
                    .with_milestone("v1-0")
                    .build(),
                    IssueBuilder()
                    .with_title("Issue 2")
                    .with_estimated_hours(16.0)
                    .with_milestone("v1-0")
                    .build(),
                ],
                "3.0d",
            ),
        ],
    )
    def test_milestone_estimated_time_display(self, issues, expected_display):
        """Test milestone estimated time display formatting."""
        milestone = MilestoneBuilder().with_name("v1-0").build()
        assert milestone.get_estimated_time_display(issues) == expected_display
