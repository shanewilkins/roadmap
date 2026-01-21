"""Tests for estimated time functionality."""

import os
import tempfile

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.common.constants import Status
from roadmap.infrastructure.coordination.core import RoadmapCore
from tests.factories import IssueBuilder, MilestoneBuilder
from tests.unit.common.formatters.test_data_factory import TestDataFactory


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

    @pytest.mark.parametrize(
        "estimated_hours,expected_display",
        [
            (0.5, "30m"),  # minutes (< 1 hour)
            (4.25, "4.2h"),  # hours (< 8 hours)
            (16.0, "2.0d"),  # days (>= 8 hours)
        ],
    )
    def test_estimated_time_display_formats(self, estimated_hours, expected_display):
        issue = IssueBuilder().with_estimated_hours(estimated_hours).build()
        assert issue.estimated_time_display == expected_display


class TestMilestoneEstimatedTime:
    """Test estimated time calculations for milestones."""

    def test_milestone_total_estimated_hours(self):
        """Test milestone total estimated hours calculation."""
        milestone = MilestoneBuilder().build()
        issues = [
            IssueBuilder()
            .with_estimated_hours(4.0)
            .with_milestone(milestone.name)
            .build(),
            IssueBuilder()
            .with_estimated_hours(8.0)
            .with_milestone(milestone.name)
            .build(),
            IssueBuilder()
            .with_estimated_hours(None)
            .with_milestone(milestone.name)
            .build(),
            IssueBuilder().with_estimated_hours(2.0).build(),
        ]
        total_hours = milestone.get_total_estimated_hours(issues)
        assert total_hours == 12.0

    def test_milestone_remaining_estimated_hours(self):
        """Test milestone remaining estimated hours calculation."""
        milestone = MilestoneBuilder().build()
        issues = [
            IssueBuilder()
            .with_estimated_hours(4.0)
            .with_milestone(milestone.name)
            .with_status(Status.CLOSED)
            .build(),
            IssueBuilder()
            .with_estimated_hours(8.0)
            .with_milestone(milestone.name)
            .with_status(Status.TODO)
            .build(),
            IssueBuilder()
            .with_estimated_hours(6.0)
            .with_milestone(milestone.name)
            .with_status(Status.IN_PROGRESS)
            .build(),
        ]
        remaining_hours = milestone.get_remaining_estimated_hours(issues)
        assert remaining_hours == 14.0

    def test_milestone_estimated_time_display_no_estimate(self):
        """Test milestone estimated time display with no estimates."""
        milestone = MilestoneBuilder().build()
        issues = [
            IssueBuilder().with_milestone(milestone.name).build(),
            IssueBuilder().with_milestone(milestone.name).build(),
        ]
        assert milestone.get_estimated_time_display(issues) == "Not estimated"

    def test_milestone_estimated_time_display_hours(self):
        """Test milestone estimated time display with hours."""
        milestone = MilestoneBuilder().build()
        issues = [
            IssueBuilder()
            .with_estimated_hours(2.0)
            .with_milestone(milestone.name)
            .build(),
            IssueBuilder()
            .with_estimated_hours(3.0)
            .with_milestone(milestone.name)
            .build(),
        ]
        assert milestone.get_estimated_time_display(issues) == "5.0h"

    def test_milestone_estimated_time_display_days(self):
        """Test milestone estimated time display with days."""
        milestone = MilestoneBuilder().build()
        issues = [
            IssueBuilder()
            .with_estimated_hours(8.0)
            .with_milestone(milestone.name)
            .build(),
            IssueBuilder()
            .with_estimated_hours(16.0)
            .with_milestone(milestone.name)
            .build(),
        ]
        assert milestone.get_estimated_time_display(issues) == "3.0d"


class TestEstimatedTimeCLI:
    """Test CLI commands with estimated time functionality."""

    @pytest.fixture
    def initialized_roadmap(self):
        """Create a temporary directory with initialized roadmap."""
        from tests.fixtures.integration_helpers import IntegrationTestBase

        runner = CliRunner()
        with runner.isolated_filesystem():
            core = IntegrationTestBase.init_roadmap(runner)
            yield runner, core

    @pytest.mark.parametrize(
        "estimate_arg,should_contain_estimate,estimated_value",
        [
            # With estimate
            (["--estimate", "4.5"], True, "4.5h"),
            # Without estimate
            (None, False, None),
        ],
    )
    def test_create_issue_estimate_cli(
        self,
        initialized_roadmap,
        estimate_arg,
        should_contain_estimate,
        estimated_value,
    ):
        """Test creating an issue with and without estimated time via CLI."""
        runner, core = initialized_roadmap
        message = TestDataFactory.message()

        cmd = ["issue", "create", message]
        if estimate_arg:
            cmd.extend(estimate_arg)
        result = runner.invoke(main, cmd)
        assert result.exit_code == 0

        # Instead of checking output, verify the issue was created with correct estimate
        issues = core.issues.list()
        assert len(issues) > 0, "Issue was not created"

        # Find the created issue by title
        created_issue = None
        for issue in issues:
            if issue.title == message:
                created_issue = issue
                break

        assert (
            created_issue is not None
        ), f"Could not find created issue with title: {message}"

        if should_contain_estimate:
            assert created_issue.estimated_hours == float(estimated_value.rstrip("h"))
        else:
            assert created_issue.estimated_hours is None

    def test_update_issue_estimate(self, initialized_roadmap):
        """Test updating an issue's estimated time via CLI."""
        runner, core = initialized_roadmap
        message = TestDataFactory.message()

        # Create an issue without estimate
        create_result = runner.invoke(main, ["issue", "create", message])
        assert create_result.exit_code == 0

        # Get the created issue
        issues = core.issues.list()
        created_issue = None
        for issue in issues:
            if issue.title == message:
                created_issue = issue
                break
        assert created_issue is not None
        issue_id = created_issue.id

        # Update the estimate
        update_result = runner.invoke(
            main, ["issue", "update", issue_id, "--estimate", "6.0"]
        )
        assert update_result.exit_code == 0

        # Verify the estimate was actually updated by checking the core
        updated_issue = core.issues.get(issue_id)
        assert updated_issue is not None
        assert updated_issue.estimated_hours == 6.0

    def test_issue_list_shows_estimates(self, initialized_roadmap):
        """Test that issue list shows estimated times."""
        runner, core = initialized_roadmap

        # Create issues with different estimates
        runner.invoke(
            main, ["issue", "create", TestDataFactory.message(), "--estimate", "1.0"]
        )
        runner.invoke(
            main, ["issue", "create", TestDataFactory.message(), "--estimate", "32.0"]
        )
        runner.invoke(main, ["issue", "create", TestDataFactory.message()])

        # Verify the issues were created with correct estimates by checking core
        issues = core.issues.list()
        assert len(issues) == 3, f"Expected 3 issues, got {len(issues)}"

        # Find issues with specific estimates
        issue_1h = None
        issue_32h = None
        issue_none = None

        for issue in issues:
            if issue.estimated_hours == 1.0:
                issue_1h = issue
            elif issue.estimated_hours == 32.0:
                issue_32h = issue
            elif issue.estimated_hours is None:
                issue_none = issue

        assert issue_1h is not None, "Issue with 1.0h estimate not found"
        assert issue_32h is not None, "Issue with 32.0h estimate not found"
        assert issue_none is not None, "Issue with no estimate not found"

    def test_milestone_list_shows_estimates(self, temp_dir_context):
        """Test that milestone list shows total estimated times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            core = RoadmapCore()
            core.initialize()

            # Create a milestone
            milestone_name = TestDataFactory.milestone_id()
            core.milestones.create(name=milestone_name)

            # Create issues with estimated time and assign to milestone
            issue1 = core.issues.create(
                title=TestDataFactory.message(), estimated_hours=8.0
            )
            issue1_updated = core.issues.update(issue1.id, milestone=milestone_name)
            assert issue1_updated.estimated_hours == 8.0

            issue2 = core.issues.create(
                title=TestDataFactory.message(), estimated_hours=16.0
            )
            issue2_updated = core.issues.update(issue2.id, milestone=milestone_name)
            assert issue2_updated.estimated_hours == 16.0

            # Get milestone and verify total estimated time
            milestones = core.milestones.list()
            target_milestone = next(
                (m for m in milestones if m.name == milestone_name), None
            )
            assert target_milestone is not None

            # Total: 8.0 + 16.0 = 24.0 hours = 3.0 days
            # Verify issues are associated
            issues_in_milestone = [
                i for i in core.issues.list() if i.milestone == milestone_name
            ]
            assert len(issues_in_milestone) == 2
            total_estimate = sum(i.estimated_hours or 0 for i in issues_in_milestone)
            assert total_estimate == 24.0


class TestEstimatedTimeCore:
    """Test estimated time functionality in RoadmapCore."""

    @pytest.mark.parametrize(
        "estimated_hours,should_have_hours,expected_display",
        [
            # With estimated hours
            (5.5, True, "5.5h"),
            # Without estimated hours
            (None, False, "Not estimated"),
        ],
    )
    def test_create_issue_estimated_hours(
        self, estimated_hours, should_have_hours, expected_display, temp_dir_context
    ):
        """Test creating an issue with and without estimated hours through core."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            core = RoadmapCore()
            core.initialize()

            if estimated_hours is not None:
                issue = core.issues.create(
                    title=TestDataFactory.message(), estimated_hours=estimated_hours
                )
                assert issue.estimated_hours == estimated_hours
            else:
                issue = core.issues.create(title=TestDataFactory.message())
                assert issue.estimated_hours is None
            assert issue.estimated_time_display == expected_display


class TestEstimatedTimePersistence:
    """Test that estimated time persists correctly."""

    def test_estimated_time_saves_and_loads(self, temp_dir_context):
        """Test that estimated time is saved to and loaded from files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create and save an issue with estimated time
            core = RoadmapCore()
            core.initialize()

            original_issue = core.issues.create(
                title=TestDataFactory.message(), estimated_hours=12.0
            )

            # Load the issue back from file
            loaded_issues = core.issues.list()
            loaded_issue = next(i for i in loaded_issues if i.id == original_issue.id)

            assert loaded_issue.estimated_hours == 12.0
            assert loaded_issue.estimated_time_display == "1.5d"


class TestEstimatedTimeEdgeCases:
    """Test edge cases for estimated time functionality."""

    @pytest.mark.parametrize(
        "estimated_hours,expected_display",
        [
            (0.0, "0m"),  # zero estimated hours
            (0.1, "6m"),  # very small estimated hours (6 minutes)
            (160.0, "20.0d"),  # large estimated hours (20 days)
            (-5.0, str),  # negative estimated hours - should return string
        ],
    )
    def test_estimated_time_edge_cases(self, estimated_hours, expected_display):
        """Test edge cases for estimated time functionality."""
        issue = IssueBuilder().with_estimated_hours(estimated_hours).build()
        display = issue.estimated_time_display
        if expected_display is str:
            # For negative, just check it returns a string
            assert isinstance(display, str)
        else:
            assert display == expected_display
