"""Tests for domain object builders.

Ensures that all builders create valid objects and that the fluent
interface works correctly.
"""

from datetime import UTC, datetime, timedelta

import pytest

from roadmap.common.constants import (
    IssueType,
    MilestoneStatus,
    Priority,
    ProjectStatus,
    RiskLevel,
    Status,
)
from roadmap.core.domain import Issue, Milestone, Project
from tests.factories import IssueBuilder, MilestoneBuilder, ProjectBuilder


class TestIssueBuilder:
    """Test IssueBuilder functionality."""

    def test_builder_creates_valid_issue(self):
        """Test that builder creates a valid Issue object."""
        issue = IssueBuilder().build()

        assert isinstance(issue, Issue)
        assert issue.title == "Test Issue"
        assert issue.priority == Priority.MEDIUM
        assert issue.status == Status.TODO

    def test_builder_fluent_interface_chaining(self):
        """Test that fluent interface methods can be chained."""
        issue = (
            IssueBuilder()
            .with_title("My Issue")
            .with_priority(Priority.HIGH)
            .with_status(Status.IN_PROGRESS)
            .build()
        )

        assert issue.title == "My Issue"
        assert issue.priority == Priority.HIGH
        assert issue.status == Status.IN_PROGRESS

    def test_builder_with_id(self):
        """Test setting custom issue ID."""
        issue = IssueBuilder().with_id("custom-id").build()
        assert issue.id == "custom-id"

    def test_builder_with_title(self):
        """Test setting custom title."""
        issue = IssueBuilder().with_title("Fix critical bug").build()
        assert issue.title == "Fix critical bug"

    @pytest.mark.parametrize(
        "priority",
        [
            Priority.LOW,
            Priority.MEDIUM,
            Priority.HIGH,
            Priority.CRITICAL,
        ],
    )
    def test_builder_with_priority_levels(self, priority):
        """Test setting all priority levels."""
        issue = IssueBuilder().with_priority(priority).build()
        assert issue.priority == priority

    @pytest.mark.parametrize(
        "status",
        [Status.TODO, Status.IN_PROGRESS, Status.BLOCKED, Status.CLOSED],
    )
    def test_builder_with_statuses(self, status):
        """Test setting all issue statuses."""
        issue = IssueBuilder().with_status(status).build()
        assert issue.status == status

    @pytest.mark.parametrize(
        "issue_type",
        [IssueType.FEATURE, IssueType.BUG, IssueType.OTHER],
    )
    def test_builder_with_types(self, issue_type):
        """Test setting all issue types."""
        issue = IssueBuilder().with_type(issue_type).build()
        assert issue.issue_type == issue_type

    def test_builder_with_milestone(self):
        """Test setting milestone."""
        issue = IssueBuilder().with_milestone("v1.0").build()
        assert issue.milestone == "v1.0"

    def test_builder_with_none_milestone(self):
        """Test setting milestone to None."""
        issue = IssueBuilder().with_milestone(None).build()
        assert issue.milestone is None

    def test_builder_with_assignee(self):
        """Test setting assignee."""
        issue = IssueBuilder().with_assignee("alice").build()
        assert issue.assignee == "alice"

    def test_builder_with_labels(self):
        """Test setting multiple labels."""
        labels = ["bug", "urgent", "frontend"]
        issue = IssueBuilder().with_labels(labels).build()
        assert issue.labels == labels

    def test_builder_add_single_label(self):
        """Test adding labels one at a time."""
        issue = IssueBuilder().with_label("bug").with_label("urgent").build()

        assert "bug" in issue.labels
        assert "urgent" in issue.labels
        assert len(issue.labels) == 2

    def test_builder_with_content(self):
        """Test setting markdown content."""
        content = "## Description\n\nThis is a test issue"
        issue = IssueBuilder().with_content(content).build()
        assert issue.content == content

    def test_builder_with_estimated_hours(self):
        """Test setting estimated hours."""
        issue = IssueBuilder().with_estimated_hours(8.5).build()
        assert issue.estimated_hours == 8.5

    def test_builder_with_zero_estimated_hours(self):
        """Test setting estimated hours to zero."""
        issue = IssueBuilder().with_estimated_hours(0).build()
        assert issue.estimated_hours == 0

    def test_builder_with_progress(self):
        """Test setting progress percentage."""
        issue = IssueBuilder().with_progress(50.0).build()
        assert issue.progress_percentage == 50.0

    def test_builder_with_github_issue(self):
        """Test linking to GitHub issue."""
        issue = IssueBuilder().with_github_issue(42).build()
        assert issue.github_issue == 42

    def test_builder_with_github_issue_string(self):
        """Test linking to GitHub issue with string number."""
        issue = IssueBuilder().with_github_issue("42").build()
        assert issue.github_issue == 42

    def test_builder_with_due_date(self):
        """Test setting due date."""
        due_date = datetime.now(UTC)
        issue = IssueBuilder().with_due_date(due_date).build()
        assert issue.due_date == due_date

    def test_builder_with_dates(self):
        """Test setting created and updated dates."""
        now = datetime.now(UTC)
        later = now + timedelta(hours=1)

        issue = IssueBuilder().with_created_date(now).with_updated_date(later).build()

        assert issue.created == now
        assert issue.updated == later

    def test_builder_with_dependencies(self):
        """Test setting issue dependencies."""
        deps = ["issue-1", "issue-2"]
        issue = IssueBuilder().with_dependencies(deps).build()
        assert issue.depends_on == deps

    def test_builder_with_blocked_issues(self):
        """Test setting issues this one blocks."""
        blocks = ["issue-3", "issue-4"]
        issue = IssueBuilder().with_blocked_issues(blocks).build()
        assert issue.blocks == blocks

    def test_builder_with_git_branches(self):
        """Test setting git branches."""
        branches = ["feature/auth", "feature/api"]
        issue = IssueBuilder().with_git_branches(branches).build()
        assert issue.git_branches == branches

    def test_builder_clone(self):
        """Test cloning a builder preserves state."""
        original = IssueBuilder().with_title("Original").with_priority(Priority.HIGH)
        cloned = original.clone().with_title("Cloned")

        original_issue = original.build()
        cloned_issue = cloned.build()

        assert original_issue.title == "Original"
        assert cloned_issue.title == "Cloned"
        assert original_issue.priority == cloned_issue.priority


class TestMilestoneBuilder:
    """Test MilestoneBuilder functionality."""

    def test_builder_creates_valid_milestone(self):
        """Test that builder creates a valid Milestone object."""
        milestone = MilestoneBuilder().build()

        assert isinstance(milestone, Milestone)
        assert milestone.name == "Test Milestone"
        assert milestone.status == MilestoneStatus.OPEN

    def test_builder_fluent_interface_chaining(self):
        """Test that fluent interface methods can be chained."""
        milestone = (
            MilestoneBuilder()
            .with_name("v1.0")
            .with_status(MilestoneStatus.OPEN)
            .with_content("First release")
            .build()
        )

        assert milestone.name == "v1.0"
        assert milestone.status == MilestoneStatus.OPEN
        assert milestone.content == "First release"

    def test_builder_with_name(self):
        """Test setting custom name."""
        milestone = MilestoneBuilder().with_name("v2.0").build()
        assert milestone.name == "v2.0"

    def test_builder_with_description(self):
        """Test setting description."""
        milestone = MilestoneBuilder().with_content("Major update").build()
        assert milestone.content == "Major update"

    @pytest.mark.parametrize(
        "status",
        [MilestoneStatus.OPEN, MilestoneStatus.CLOSED],
    )
    def test_builder_with_milestone_statuses(self, status):
        """Test setting all milestone statuses."""
        milestone = MilestoneBuilder().with_status(status).build()
        assert milestone.status == status

    def test_builder_with_due_date(self):
        """Test setting due date."""
        due_date = datetime.now(UTC)
        milestone = MilestoneBuilder().with_due_date(due_date).build()
        assert milestone.due_date == due_date

    def test_builder_with_progress(self):
        """Test setting progress percentage."""
        milestone = MilestoneBuilder().with_progress(75.0).build()
        assert milestone.calculated_progress == 75.0

    def test_builder_with_risk_level(self):
        """Test setting risk level."""
        milestone = MilestoneBuilder().with_risk_level(RiskLevel.HIGH).build()
        assert milestone.risk_level == RiskLevel.HIGH

    def test_builder_with_content(self):
        """Test setting markdown content."""
        content = "## Goals\n\n- Goal 1\n- Goal 2"
        milestone = MilestoneBuilder().with_content(content).build()
        assert milestone.content == content

    def test_builder_with_github_milestone(self):
        """Test linking to GitHub milestone."""
        milestone = MilestoneBuilder().with_github_milestone(1).build()
        assert milestone.github_milestone == 1

    def test_builder_with_dates(self):
        """Test setting created and updated dates."""
        now = datetime.now(UTC)
        later = now + timedelta(days=1)

        milestone = (
            MilestoneBuilder().with_created_date(now).with_updated_date(later).build()
        )

        assert milestone.created == now
        assert milestone.updated == later

    def test_builder_with_start_and_end_dates(self):
        """Test setting actual start and end dates."""
        start = datetime.now(UTC)
        end = start + timedelta(days=30)

        milestone = MilestoneBuilder().with_start_date(start).with_end_date(end).build()

        assert milestone.actual_start_date == start
        assert milestone.actual_end_date == end

    def test_builder_clone(self):
        """Test cloning a builder preserves state."""
        original = (
            MilestoneBuilder().with_name("v1.0").with_status(MilestoneStatus.OPEN)
        )
        cloned = original.clone().with_name("v2.0")

        original_milestone = original.build()
        cloned_milestone = cloned.build()

        assert original_milestone.name == "v1.0"
        assert cloned_milestone.name == "v2.0"
        assert original_milestone.status == cloned_milestone.status


class TestProjectBuilder:
    """Test ProjectBuilder functionality."""

    def test_builder_creates_valid_project(self):
        """Test that builder creates a valid Project object."""
        project = ProjectBuilder().build()

        assert isinstance(project, Project)
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.PLANNING

    def test_builder_fluent_interface_chaining(self):
        """Test that fluent interface methods can be chained."""
        project = (
            ProjectBuilder()
            .with_name("Roadmap")
            .with_status(ProjectStatus.ACTIVE)
            .with_description("Project management tool")
            .build()
        )

        assert project.name == "Roadmap"
        assert project.status == ProjectStatus.ACTIVE
        assert project.content == "Project management tool"

    def test_builder_with_id(self):
        """Test setting custom project ID."""
        project = ProjectBuilder().with_id("proj-123").build()
        assert project.id == "proj-123"

    def test_builder_with_name(self):
        """Test setting custom name."""
        project = ProjectBuilder().with_name("My Project").build()
        assert project.name == "My Project"

    def test_builder_with_description(self):
        """Test setting description."""
        project = ProjectBuilder().with_content("A test project").build()
        assert project.content == "A test project"

    def test_builder_with_all_statuses(self):
        """Test setting all project statuses."""
        for status in [
            ProjectStatus.PLANNING,
            ProjectStatus.ACTIVE,
            ProjectStatus.ON_HOLD,
            ProjectStatus.COMPLETED,
        ]:
            project = ProjectBuilder().with_status(status).build()
            assert project.status == status

    def test_builder_with_priority(self):
        """Test setting project priority."""
        project = ProjectBuilder().with_priority(Priority.HIGH).build()
        assert project.priority == Priority.HIGH

    def test_builder_with_owner(self):
        """Test setting project owner."""
        project = ProjectBuilder().with_owner("alice").build()
        assert project.owner == "alice"

    def test_builder_with_milestones(self):
        """Test setting multiple milestones."""
        milestones = ["v1.0", "v2.0", "v3.0"]
        project = ProjectBuilder().with_milestones(milestones).build()
        assert project.milestones == milestones

    def test_builder_add_single_milestone(self):
        """Test adding milestones one at a time."""
        project = ProjectBuilder().with_milestone("v1.0").with_milestone("v2.0").build()

        assert "v1.0" in project.milestones
        assert "v2.0" in project.milestones
        assert len(project.milestones) == 2

    def test_builder_with_estimated_hours(self):
        """Test setting estimated hours."""
        project = ProjectBuilder().with_estimated_hours(200).build()
        assert project.estimated_hours == 200

    def test_builder_with_actual_hours(self):
        """Test setting actual hours."""
        project = ProjectBuilder().with_actual_hours(150).build()
        assert project.actual_hours == 150

    def test_builder_with_progress(self):
        """Test setting progress percentage."""
        project = ProjectBuilder().with_progress(60.0).build()
        assert project.calculated_progress == 60.0

    def test_builder_with_risk_level(self):
        """Test setting risk level."""
        project = ProjectBuilder().with_risk_level(RiskLevel.MEDIUM).build()
        assert project.risk_level == RiskLevel.MEDIUM

    def test_builder_with_dates(self):
        """Test setting start and target end dates."""
        start = datetime.now(UTC)
        end = start + timedelta(days=90)

        project = (
            ProjectBuilder().with_start_date(start).with_target_end_date(end).build()
        )

        assert project.start_date == start
        assert project.target_end_date == end

    def test_builder_with_actual_end_date(self):
        """Test setting actual end date."""
        actual_end = datetime.now(UTC)
        project = ProjectBuilder().with_actual_end_date(actual_end).build()
        assert project.actual_end_date == actual_end

    def test_builder_with_content(self):
        """Test setting markdown content."""
        content = "## Overview\n\nProject overview here"
        project = ProjectBuilder().with_content(content).build()
        assert project.content == content

    def test_builder_with_dates_metadata(self):
        """Test setting created and updated dates."""
        now = datetime.now(UTC)
        later = now + timedelta(hours=2)

        project = (
            ProjectBuilder().with_created_date(now).with_updated_date(later).build()
        )

        assert project.created == now
        assert project.updated == later

    def test_builder_clone(self):
        """Test cloning a builder preserves state."""
        original = (
            ProjectBuilder().with_name("Original").with_status(ProjectStatus.ACTIVE)
        )
        cloned = original.clone().with_name("Cloned")

        original_project = original.build()
        cloned_project = cloned.build()

        assert original_project.name == "Original"
        assert cloned_project.name == "Cloned"
        assert original_project.status == cloned_project.status


class TestBuilderInteroperability:
    """Test that builders work well together."""

    def test_issue_with_milestone_reference(self):
        """Test creating issue that references milestone."""
        milestone = MilestoneBuilder().with_name("v1.0").build()
        issue = IssueBuilder().with_milestone(milestone.name).build()

        assert issue.milestone == milestone.name

    def test_multiple_issues_for_same_milestone(self):
        """Test creating multiple issues for same milestone."""
        milestone = MilestoneBuilder().with_name("v1.0").build()

        issues = [
            IssueBuilder()
            .with_title(f"Issue {i}")
            .with_milestone(milestone.name)
            .build()
            for i in range(3)
        ]

        assert len(issues) == 3
        assert all(issue.milestone == milestone.name for issue in issues)

    def test_project_with_milestones(self):
        """Test creating project with multiple milestones."""
        project = (
            ProjectBuilder()
            .with_name("Test Project")
            .with_milestone("v1.0")
            .with_milestone("v2.0")
            .build()
        )

        assert len(project.milestones) == 2
        assert "v1.0" in project.milestones
        assert "v2.0" in project.milestones
