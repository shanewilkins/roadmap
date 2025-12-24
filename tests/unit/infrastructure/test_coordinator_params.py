"""Tests for coordinator parameters dataclasses."""

from datetime import datetime

from roadmap.core.domain import IssueType, Priority
from roadmap.infrastructure.coordinator_params import (
    IssueCreateParams,
    IssueListParams,
    IssueUpdateParams,
    MilestoneCreateParams,
    MilestoneUpdateParams,
    ProjectCreateParams,
    ProjectUpdateParams,
)


class TestIssueCreateParams:
    """Test IssueCreateParams dataclass."""

    def test_create_with_defaults(self):
        """Test creating IssueCreateParams with defaults - title and type."""
        params = IssueCreateParams(title="Test Issue")
        assert params.title == "Test Issue"
        assert params.priority == Priority.MEDIUM
        assert params.issue_type == IssueType.OTHER

    def test_create_with_defaults_milestone_and_labels(self):
        """Test creating IssueCreateParams with defaults - milestone and labels."""
        params = IssueCreateParams(title="Test Issue")
        assert params.milestone is None
        assert params.labels is None

    def test_create_with_defaults_assignee_and_time(self):
        """Test creating IssueCreateParams with defaults - assignee and time."""
        params = IssueCreateParams(title="Test Issue")
        assert params.assignee is None
        assert params.estimated_hours is None

    def test_create_with_defaults_dependencies(self):
        """Test creating IssueCreateParams with defaults - dependencies."""
        params = IssueCreateParams(title="Test Issue")
        assert params.depends_on is None
        assert params.blocks is None

    def test_create_with_all_fields(self):
        """Test creating IssueCreateParams with all fields."""
        params = IssueCreateParams(
            title="Test Issue",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE,
            milestone="v1.0",
            labels=["bug", "urgent"],
            assignee="john@example.com",
            estimated_hours=5.5,
            depends_on=["issue-1"],
            blocks=["issue-2"],
        )
        assert params.title == "Test Issue"
        assert params.priority == Priority.HIGH
        assert params.issue_type == IssueType.FEATURE

    def test_create_with_all_fields_milestone_and_labels(self):
        """Test creating IssueCreateParams milestone and labels."""
        params = IssueCreateParams(
            title="Test Issue",
            milestone="v1.0",
            labels=["bug", "urgent"],
        )
        assert params.milestone == "v1.0"
        assert params.labels == ["bug", "urgent"]

    def test_create_with_all_fields_assignee_and_time(self):
        """Test creating IssueCreateParams with assignee and estimated time."""
        params = IssueCreateParams(
            title="Test Issue",
            assignee="john@example.com",
            estimated_hours=5.5,
        )
        assert params.assignee == "john@example.com"
        assert params.estimated_hours == 5.5

    def test_create_with_all_fields_dependencies(self):
        """Test creating IssueCreateParams with dependencies."""
        params = IssueCreateParams(
            title="Test Issue",
            depends_on=["issue-1"],
            blocks=["issue-2"],
        )
        assert params.depends_on == ["issue-1"]
        assert params.blocks == ["issue-2"]


class TestIssueListParams:
    """Test IssueListParams dataclass."""

    def test_create_with_defaults(self):
        """Test creating IssueListParams with defaults."""
        params = IssueListParams()
        assert params.milestone is None
        assert params.status is None
        assert params.priority is None
        assert params.issue_type is None
        assert params.assignee is None

    def test_create_with_filters(self):
        """Test creating IssueListParams with filters."""
        params = IssueListParams(
            milestone="v1.0",
            status="open",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
            assignee="john@example.com",
        )
        assert params.milestone == "v1.0"
        assert params.status == "open"
        assert params.priority == Priority.HIGH
        assert params.issue_type == IssueType.BUG
        assert params.assignee == "john@example.com"


class TestIssueUpdateParams:
    """Test IssueUpdateParams dataclass."""

    def test_create_with_defaults(self):
        """Test creating IssueUpdateParams with defaults."""
        params = IssueUpdateParams(issue_id="issue-1")
        assert params.issue_id == "issue-1"
        assert params.updates == {}

    def test_create_with_updates(self):
        """Test creating IssueUpdateParams with updates."""
        updates = {"status": "done", "priority": Priority.LOW}
        params = IssueUpdateParams(issue_id="issue-1", updates=updates)
        assert params.issue_id == "issue-1"
        assert params.updates == updates


class TestMilestoneCreateParams:
    """Test MilestoneCreateParams dataclass."""

    def test_create_with_defaults(self):
        """Test creating MilestoneCreateParams with defaults."""
        params = MilestoneCreateParams(name="v1.0")
        assert params.name == "v1.0"
        assert params.description == ""
        assert params.due_date is None

    def test_create_with_all_fields(self):
        """Test creating MilestoneCreateParams with all fields."""
        due_date = datetime(2025, 12, 31)
        params = MilestoneCreateParams(
            name="v1.0",
            description="Release version 1.0",
            due_date=due_date,
        )
        assert params.name == "v1.0"
        assert params.description == "Release version 1.0"
        assert params.due_date == due_date


class TestMilestoneUpdateParams:
    """Test MilestoneUpdateParams dataclass."""

    def test_create_with_defaults(self):
        """Test creating MilestoneUpdateParams with defaults."""
        params = MilestoneUpdateParams(name="v1.0")
        assert params.name == "v1.0"
        assert params.description is None
        assert params.due_date is None
        assert not params.clear_due_date
        assert params.status is None

    def test_create_with_all_fields(self):
        """Test creating MilestoneUpdateParams with all fields."""
        due_date = datetime(2025, 12, 31)
        params = MilestoneUpdateParams(
            name="v1.0",
            description="Updated description",
            due_date=due_date,
            clear_due_date=False,
            status="completed",
        )
        assert params.name == "v1.0"
        assert params.description == "Updated description"
        assert params.due_date == due_date
        assert not params.clear_due_date
        assert params.status == "completed"

    def test_clear_due_date(self):
        """Test creating MilestoneUpdateParams with clear_due_date."""
        params = MilestoneUpdateParams(
            name="v1.0",
            clear_due_date=True,
        )
        assert params.clear_due_date
        assert params.due_date is None


class TestProjectCreateParams:
    """Test ProjectCreateParams dataclass."""

    def test_create_with_defaults(self):
        """Test creating ProjectCreateParams with defaults."""
        params = ProjectCreateParams(name="My Project")
        assert params.name == "My Project"
        assert params.description == ""
        assert params.milestones is None

    def test_create_with_all_fields(self):
        """Test creating ProjectCreateParams with all fields."""
        params = ProjectCreateParams(
            name="My Project",
            description="Project description",
            milestones=["v1.0", "v1.1"],
        )
        assert params.name == "My Project"
        assert params.description == "Project description"
        assert params.milestones == ["v1.0", "v1.1"]


class TestProjectUpdateParams:
    """Test ProjectUpdateParams dataclass."""

    def test_create_with_defaults(self):
        """Test creating ProjectUpdateParams with defaults."""
        params = ProjectUpdateParams(project_id="proj-1")
        assert params.project_id == "proj-1"
        assert params.updates == {}

    def test_create_with_updates(self):
        """Test creating ProjectUpdateParams with updates."""
        updates = {"name": "Updated Project", "description": "New description"}
        params = ProjectUpdateParams(project_id="proj-1", updates=updates)
        assert params.project_id == "proj-1"
        assert params.updates == updates
