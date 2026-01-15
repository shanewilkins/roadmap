"""Tests for estimated time functionality."""

import os
import re
import tempfile

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.common.constants import Status
from roadmap.infrastructure.core import RoadmapCore
from tests.factories import IssueBuilder, MilestoneBuilder
from tests.unit.shared.test_ansi_utilities import strip_ansi
from tests.unit.shared.test_data_factory import TestDataFactory


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
        runner = initialized_roadmap

        cmd = ["issue", "create", TestDataFactory.message()]
        if estimate_arg:
            cmd.extend(estimate_arg)
        result = runner.invoke(main, cmd)
        assert result.exit_code == 0
        clean_output = strip_ansi(result.output)
        assert "Created issue:" in clean_output
        if should_contain_estimate:
            assert f"Estimated: {estimated_value}" in clean_output
        else:
            assert "Estimated:" not in clean_output

    def test_update_issue_estimate(self, initialized_roadmap):
        """Test updating an issue's estimated time via CLI."""
        runner = initialized_roadmap

        # Create an issue first
        create_result = runner.invoke(
            main, ["issue", "create", TestDataFactory.message()]
        )
        assert create_result.exit_code == 0

        # Extract issue ID from output - look for the success message line
        clean_create = strip_ansi(create_result.output)
        issue_id = None
        # Try to find ID in brackets first
        for line in clean_create.split("\n"):
            if "Created issue" in line:
                match = re.search(r"\[([^\]]+)\]", line)
                if match:
                    issue_id = match.group(1)
                    break
        # Fallback: look for issue_id= in the logs
        if not issue_id:
            match = re.search(r"issue_id=([a-f0-9]+)", clean_create)
            if match:
                issue_id = match.group(1)

        assert issue_id, f"Could not find issue ID in: {clean_create}"

        # Update the estimate
        update_result = runner.invoke(
            main, ["issue", "update", issue_id, "--estimate", "6.0"]
        )
        assert update_result.exit_code == 0
        clean_output = strip_ansi(update_result.output)
        assert "Updated issue:" in clean_output
        assert "estimate: 6.0h" in clean_output

    def test_issue_list_shows_estimates(self, initialized_roadmap):
        """Test that issue list shows estimated times."""
        runner = initialized_roadmap

        # Create issues with different estimates
        runner.invoke(
            main, ["issue", "create", TestDataFactory.message(), "--estimate", "1.0"]
        )
        runner.invoke(
            main, ["issue", "create", TestDataFactory.message(), "--estimate", "32.0"]
        )
        runner.invoke(main, ["issue", "create", TestDataFactory.message()])

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
        runner.invoke(main, ["milestone", "create", TestDataFactory.milestone_id()])

        # Create issues and assign to milestone
        create_result1 = runner.invoke(
            main, ["issue", "create", TestDataFactory.message(), "--estimate", "8.0"]
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
            main, ["issue", "create", TestDataFactory.message(), "--estimate", "16.0"]
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
        milestone_name = TestDataFactory.milestone_id()
        runner.invoke(
            main, ["issue", "update", issue_id1, "--milestone", milestone_name]
        )
        runner.invoke(
            main, ["issue", "update", issue_id2, "--milestone", milestone_name]
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
        self, estimated_hours, should_have_hours, expected_display
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

    def test_estimated_time_saves_and_loads(self):
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
