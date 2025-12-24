"""Tests for CLI DTOs and mappers."""

from datetime import datetime, timedelta

from roadmap.adapters.cli.dtos import IssueDTO, MilestoneDTO, ProjectDTO
from roadmap.adapters.cli.mappers import IssueMapper, MilestoneMapper, ProjectMapper
from roadmap.common.constants import (
    IssueType,
    MilestoneStatus,
    Priority,
    ProjectStatus,
    Status,
)
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project


class TestIssueDTO:
    """Test IssueDTO class."""

    def test_issue_dto_creation(self):
        """Test creating an IssueDTO."""
        dto = IssueDTO(
            id="issue-1",
            title="Test issue",
            priority="high",
            status="in_progress",
            assignee="alice",
        )

        assert dto.id == "issue-1"
        assert dto.title == "Test issue"
        assert dto.priority == "high"
        assert dto.status == "in_progress"
        assert dto.assignee == "alice"

    def test_issue_dto_from_dict(self):
        """Test creating IssueDTO from dictionary."""
        data = {
            "id": "issue-2",
            "title": "Feature request",
            "priority": "medium",
            "status": "todo",
        }

        dto = IssueDTO.from_dict(data)

        assert dto.id == "issue-2"
        assert dto.title == "Feature request"
        assert dto.priority == "medium"
        assert dto.status == "todo"

    def test_issue_dto_from_dict_ignores_unknown_fields(self):
        """Test that from_dict ignores unknown fields."""
        data = {
            "id": "issue-3",
            "title": "Bug",
            "priority": "high",
            "status": "done",
            "unknown_field": "should be ignored",
        }

        dto = IssueDTO.from_dict(data)

        assert dto.id == "issue-3"
        assert not hasattr(dto, "unknown_field")


class TestMilestoneDTO:
    """Test MilestoneDTO class."""

    def test_milestone_dto_creation(self):
        """Test creating a MilestoneDTO."""
        due_date = datetime.now() + timedelta(days=10)
        dto = MilestoneDTO(
            id="v1.0",
            name="v1.0",
            status="open",
            due_date=due_date,
        )

        assert dto.id == "v1.0"
        assert dto.name == "v1.0"
        assert dto.status == "open"
        assert dto.due_date == due_date

    def test_milestone_dto_from_dict(self):
        """Test creating MilestoneDTO from dictionary."""
        data = {
            "id": "v2.0",
            "name": "v2.0",
            "status": "closed",
            "progress_percentage": 100.0,
        }

        dto = MilestoneDTO.from_dict(data)

        assert dto.id == "v2.0"
        assert dto.progress_percentage == 100.0


class TestProjectDTO:
    """Test ProjectDTO class."""

    def test_project_dto_creation(self):
        """Test creating a ProjectDTO."""
        dto = ProjectDTO(
            id="proj-1",
            name="My Project",
            status="active",
            owner="alice",
        )

        assert dto.id == "proj-1"
        assert dto.name == "My Project"
        assert dto.status == "active"
        assert dto.owner == "alice"


class TestIssueMapper:
    """Test IssueMapper."""

    def test_domain_to_dto_converts_enums_to_strings(self):
        """Test that domain_to_dto converts enums to strings."""
        issue = Issue(
            id="issue-1",
            title="Test",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            issue_type=IssueType.BUG,
            assignee="alice",
        )

        dto = IssueMapper.domain_to_dto(issue)

        assert isinstance(dto.priority, str)
        assert dto.priority == "high"
        assert isinstance(dto.status, str)
        assert dto.status == "in-progress"  # Status uses dashes
        assert isinstance(dto.issue_type, str)
        assert dto.issue_type == "bug"

    def test_domain_to_dto_preserves_fields(self):
        """Test that domain_to_dto preserves all important fields - basic."""
        now = datetime.now()
        issue = Issue(
            id="issue-2",
            title="Feature",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="bob",
            milestone="v1.0",
            due_date=now,
            estimated_hours=5.0,
            content="Description here",
            labels=["bug", "urgent"],
        )

        dto = IssueMapper.domain_to_dto(issue)

        assert dto.id == "issue-2"
        assert dto.title == "Feature"
        assert dto.assignee == "bob"

    def test_domain_to_dto_preserves_fields_milestone(self):
        """Test that domain_to_dto preserves all important fields - milestone."""
        now = datetime.now()
        issue = Issue(
            id="issue-2",
            title="Feature",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="bob",
            milestone="v1.0",
            due_date=now,
            estimated_hours=5.0,
            content="Description here",
            labels=["bug", "urgent"],
        )

        dto = IssueMapper.domain_to_dto(issue)

        assert dto.milestone == "v1.0"
        assert dto.due_date == now
        assert dto.estimated_hours == 5.0

    def test_domain_to_dto_preserves_fields_content(self):
        """Test that domain_to_dto preserves all important fields - content."""
        now = datetime.now()
        issue = Issue(
            id="issue-2",
            title="Feature",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="bob",
            milestone="v1.0",
            due_date=now,
            estimated_hours=5.0,
            content="Description here",
            labels=["bug", "urgent"],
        )

        dto = IssueMapper.domain_to_dto(issue)

        assert dto.content == "Description here"
        assert dto.labels == ["bug", "urgent"]

    def test_dto_to_domain_converts_strings_back_to_enums(self):
        """Test that dto_to_domain converts strings back to enums."""
        dto = IssueDTO(
            id="issue-3",
            title="Test",
            priority="high",
            status="in-progress",  # Status uses dashes
            issue_type="feature",
        )

        issue = IssueMapper.dto_to_domain(dto)

        assert isinstance(issue.priority, Priority)
        assert issue.priority == Priority.HIGH
        assert isinstance(issue.status, Status)
        assert issue.status == Status.IN_PROGRESS
        assert isinstance(issue.issue_type, IssueType)
        assert issue.issue_type == IssueType.FEATURE

    def test_roundtrip_conversion_basic_fields(self):
        """Test that domain -> DTO -> domain preserves basic fields."""
        original = Issue(
            id="issue-4",
            title="Roundtrip test",
            priority=Priority.HIGH,
            status=Status.CLOSED,
            issue_type=IssueType.FEATURE,
            assignee="charlie",
            milestone="v2.0",
            estimated_hours=8.0,
        )

        # Convert to DTO and back
        dto = IssueMapper.domain_to_dto(original)
        roundtrip = IssueMapper.dto_to_domain(dto)

        # Verify basic fields match
        assert roundtrip.id == original.id
        assert roundtrip.title == original.title
        assert roundtrip.priority == original.priority

    def test_roundtrip_conversion_status_and_assignee(self):
        """Test that domain -> DTO -> domain preserves status and assignee."""
        original = Issue(
            id="issue-4",
            title="Roundtrip test",
            priority=Priority.HIGH,
            status=Status.CLOSED,
            issue_type=IssueType.FEATURE,
            assignee="charlie",
            milestone="v2.0",
            estimated_hours=8.0,
        )

        # Convert to DTO and back
        dto = IssueMapper.domain_to_dto(original)
        roundtrip = IssueMapper.dto_to_domain(dto)

        # Verify status and assignee match
        assert roundtrip.status == original.status
        assert roundtrip.assignee == original.assignee

    def test_roundtrip_conversion_milestone_and_hours(self):
        """Test that domain -> DTO -> domain preserves milestone and estimated hours."""
        original = Issue(
            id="issue-4",
            title="Roundtrip test",
            priority=Priority.HIGH,
            status=Status.CLOSED,
            issue_type=IssueType.FEATURE,
            assignee="charlie",
            milestone="v2.0",
            estimated_hours=8.0,
        )

        # Convert to DTO and back
        dto = IssueMapper.domain_to_dto(original)
        roundtrip = IssueMapper.dto_to_domain(dto)

        # Verify milestone and hours match
        assert roundtrip.milestone == original.milestone
        assert roundtrip.estimated_hours == original.estimated_hours


class TestMilestoneMapper:
    """Test MilestoneMapper."""

    def test_domain_to_dto_converts_status_to_string(self):
        """Test that domain_to_dto converts status enum to string."""
        milestone = Milestone(
            name="v1.0",
            status=MilestoneStatus.OPEN,
            due_date=datetime.now(),
        )

        dto = MilestoneMapper.domain_to_dto(milestone)

        assert isinstance(dto.status, str)
        assert dto.status == "open"

    def test_dto_to_domain_converts_string_back_to_enum(self):
        """Test that dto_to_domain converts string back to enum."""
        dto = MilestoneDTO(
            id="v1.0",
            name="v1.0",
            status="closed",
        )

        milestone = MilestoneMapper.dto_to_domain(dto)

        assert isinstance(milestone.status, MilestoneStatus)
        assert milestone.status == MilestoneStatus.CLOSED


class TestProjectMapper:
    """Test ProjectMapper."""

    def test_domain_to_dto_converts_status_to_string(self):
        """Test that domain_to_dto converts status enum to string."""
        project = Project(
            id="proj-1",
            name="Test Project",
            status=ProjectStatus.ACTIVE,
        )

        dto = ProjectMapper.domain_to_dto(project)

        assert isinstance(dto.status, str)
        assert dto.status == "active"

    def test_dto_to_domain_converts_string_back_to_enum(self):
        """Test that dto_to_domain converts string back to enum."""
        dto = ProjectDTO(
            id="proj-2",
            name="Test",
            status="completed",
        )

        project = ProjectMapper.dto_to_domain(dto)

        assert isinstance(project.status, ProjectStatus)
        assert project.status == ProjectStatus.COMPLETED
