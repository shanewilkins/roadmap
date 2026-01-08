"""Tests for Project domain model."""

from datetime import datetime, timedelta

import pytest

from roadmap.common.constants import Priority, ProjectStatus
from roadmap.core.domain.milestone import MilestoneStatus, RiskLevel
from roadmap.core.domain.project import Project


class TestProjectInitialization:
    """Test Project model initialization."""

    def test_project_with_required_fields(self):
        """Test creating project with only required fields."""
        project = Project(name="My Project")

        assert project.name == "My Project"
        assert project.id is not None
        assert len(project.id) == 8
        assert project.status == ProjectStatus.PLANNING
        assert project.priority == Priority.MEDIUM

    def test_project_with_all_fields(self):
        """Test creating project with all fields."""
        now = datetime.now()
        project = Project(
            id="proj001",
            name="Test Project",
            content="A test project",
            status=ProjectStatus.ACTIVE,
            priority=Priority.HIGH,
            owner="john",
            start_date=now,
            target_end_date=now + timedelta(days=30),
            estimated_hours=100.0,
            risk_level=RiskLevel.MEDIUM,
        )

        assert project.id == "proj001"
        assert project.name == "Test Project"
        assert project.content == "A test project"
        assert project.owner == "john"
        assert project.estimated_hours == 100.0

    def test_project_auto_generated_id(self):
        """Test that project ID is auto-generated."""
        p1 = Project(name="Project 1")
        p2 = Project(name="Project 2")

        assert p1.id != p2.id
        assert len(p1.id) == 8

    def test_project_timestamps(self):
        """Test that project has created and updated timestamps."""
        project = Project(name="Test")

        assert project.created is not None
        assert project.updated is not None
        assert project.created <= project.updated

    def test_project_defaults(self):
        """Test project default values."""
        project = Project(name="Test")

        assert project.status == ProjectStatus.PLANNING
        assert project.priority == Priority.MEDIUM
        assert project.content == ""
        assert project.milestones == []
        assert project.comments == []
        assert project.risk_level == RiskLevel.LOW


class TestProjectFilename:
    """Test Project filename generation."""

    @pytest.mark.parametrize(
        "name,expected_contains",
        [
            ("My Project", "my-project"),
            ("test-project", "test-project"),
            ("UPPERCASE", "uppercase"),
            ("Special@#$%Chars", "specialchars"),  # Special chars removed
            ("With-Spaces and_Underscores", "with-spaces-and_underscores"),
        ],
    )
    def test_filename_generation(self, name, expected_contains):
        """Test filename generation with various names."""
        project = Project(name=name, id="abc12345")
        filename = project.filename

        assert filename.startswith("abc12345-")
        assert expected_contains in filename
        assert filename.endswith(".md")

    def test_filename_is_unique_per_project(self):
        """Test that each project gets a unique filename."""
        p1 = Project(name="Project", id="id1")
        p2 = Project(name="Project", id="id2")

        assert p1.filename != p2.filename
        assert p1.filename.startswith("id1-")
        assert p2.filename.startswith("id2-")


class TestGetMilestones:
    """Test milestone retrieval."""

    def test_get_milestones_returns_assigned(self):
        """Test getting milestones assigned to project."""
        project = Project(name="Project", milestones=["v1.0.0", "v2.0.0"])

        milestones = [
            MilestoneStub("v1.0.0"),
            MilestoneStub("v2.0.0"),
            MilestoneStub("v3.0.0"),
        ]

        result = project.get_milestones(milestones)
        assert len(result) == 2
        assert any(m.name == "v1.0.0" for m in result)
        assert any(m.name == "v2.0.0" for m in result)

    def test_get_milestones_empty_project(self):
        """Test getting milestones from project with none assigned."""
        project = Project(name="Project", milestones=[])
        milestones = [MilestoneStub("v1.0.0")]

        result = project.get_milestones(milestones)
        assert result == []

    def test_get_milestone_count(self):
        """Test milestone count."""
        project = Project(name="Project", milestones=["v1.0.0", "v2.0.0"])

        milestones = [
            MilestoneStub("v1.0.0"),
            MilestoneStub("v2.0.0"),
            MilestoneStub("v3.0.0"),
        ]

        assert project.get_milestone_count(milestones) == 2


class TestCalculateProgress:
    """Test project progress calculation."""

    def test_progress_no_milestones(self):
        """Test progress with no milestones."""
        project = Project(name="Project", milestones=[])

        progress = project.calculate_progress([], [])
        assert progress == 0.0

    def test_progress_single_closed_milestone(self):
        """Test progress with single closed milestone."""
        project = Project(name="Project", milestones=["v1.0.0"])

        milestone = MilestoneStub("v1.0.0", status=MilestoneStatus.CLOSED)

        progress = project.calculate_progress([milestone], [])
        assert progress == 100.0

    def test_progress_partial_completion(self):
        """Test progress with partial milestone completion."""
        project = Project(name="Project", milestones=["v1.0.0"])

        milestone = MilestoneStub(
            "v1.0.0", status=MilestoneStatus.OPEN, progress_percent=50.0
        )

        progress = project.calculate_progress([milestone], [])
        assert 0 < progress < 100.0

    def test_progress_multiple_milestones_effort_weighted(self):
        """Test that progress is effort-weighted."""
        project = Project(name="Project", milestones=["v1.0.0", "v2.0.0"])

        milestones = [
            MilestoneStub(
                "v1.0.0", status=MilestoneStatus.CLOSED, estimated_hours=50.0
            ),
            MilestoneStub("v2.0.0", status=MilestoneStatus.OPEN, estimated_hours=50.0),
        ]

        progress = project.calculate_progress(milestones, [])
        # With 50 of 100 hours done, should be 50%
        assert 40 < progress < 60


class TestUpdateAutomaticFields:
    """Test automatic field updates."""

    def test_update_automatic_fields_progress(self):
        """Test that automatic fields are updated."""
        project = Project(name="Project", milestones=["v1.0.0"])

        milestone = MilestoneStub("v1.0.0", status=MilestoneStatus.CLOSED)

        project.update_automatic_fields([milestone], [])

        assert project.calculated_progress == 100.0
        assert project.last_progress_update is not None

    def test_update_automatic_fields_status_change(self):
        """Test that project status updates based on progress."""
        project = Project(
            name="Project", milestones=["v1.0.0"], status=ProjectStatus.PLANNING
        )

        milestone = MilestoneStub("v1.0.0", status=MilestoneStatus.CLOSED)

        project.update_automatic_fields([milestone], [])

        assert project.status == ProjectStatus.COMPLETED
        assert project.actual_end_date is not None

    def test_update_automatic_fields_planning_to_active(self):
        """Test project transitions from planning to active."""
        project = Project(
            name="Project", milestones=["v1.0.0"], status=ProjectStatus.PLANNING
        )

        milestone = MilestoneStub(
            "v1.0.0", status=MilestoneStatus.OPEN, progress_percent=50.0
        )

        project.update_automatic_fields([milestone], [])

        assert project.status == ProjectStatus.ACTIVE

    def test_update_automatic_fields_already_completed(self):
        """Test that actual_end_date is not reset if already set."""
        end_date = datetime.now() - timedelta(days=10)
        project = Project(
            name="Project", milestones=["v1.0.0"], actual_end_date=end_date
        )

        milestone = MilestoneStub("v1.0.0", status=MilestoneStatus.CLOSED)

        project.update_automatic_fields([milestone], [])

        assert project.actual_end_date == end_date  # Should not change


class TestProjectComments:
    """Test project comments field."""

    def test_project_has_comments_field(self):
        """Test that project has comments field."""
        project = Project(name="Project", comments=[])

        assert hasattr(project, "comments")
        assert project.comments == []

    def test_project_default_comments_empty(self):
        """Test that default comments are empty list."""
        project = Project(name="Project")

        assert project.comments == []


# Helper classes for testing
class MilestoneStub:
    """Stub for testing milestone relationships."""

    def __init__(
        self,
        name,
        status=MilestoneStatus.OPEN,
        estimated_hours=10.0,
        progress_percent=0.0,
    ):
        self.name = name
        self.status = status
        self._estimated_hours = estimated_hours
        self._progress = progress_percent

    def get_total_estimated_hours(self, issues):
        return self._estimated_hours

    def get_completion_percentage(self, issues):
        return self._progress
