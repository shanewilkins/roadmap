"""Tests for CLI presenters (IssuePresenter, MilestonePresenter, ProjectPresenter)."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.cli.dtos import IssueDTO, MilestoneDTO, ProjectDTO
from roadmap.adapters.cli.presentation.issue_presenter import IssuePresenter
from roadmap.adapters.cli.presentation.milestone_presenter import MilestonePresenter
from roadmap.adapters.cli.presentation.project_presenter import ProjectPresenter


class TestIssuePresenter:
    """Test suite for IssuePresenter."""

    def test_issue_presenter_init(self):
        """Test IssuePresenter initialization."""
        presenter = IssuePresenter()
        assert isinstance(presenter, IssuePresenter)

    def test_issue_presenter_has_render_method(self):
        """Test that IssuePresenter implements render method."""
        presenter = IssuePresenter()
        assert hasattr(presenter, "render")
        assert callable(presenter.render)

    def test_issue_presenter_render_with_full_issue_dto(self):
        """Test rendering a fully populated IssueDTO."""
        issue_dto = IssueDTO.from_dict({
            "id": "issue123",
            "title": "Test Issue",
            "priority": "high",
            "status": "in-progress",
            "issue_type": "feature",
            "assignee": "Alice",
            "milestone": "v1.0",
            "estimated_hours": 5.0,
            "progress_percentage": 50,
            "created": datetime.datetime(2024, 1, 1, 10, 0),
            "updated": datetime.datetime(2024, 1, 5, 15, 30),
            "content": "## Description\nTest description\n\n## Acceptance Criteria\nShould work",
            "labels": ["bug", "urgent"],
            "github_issue": 123,
        })

        presenter = IssuePresenter()
        # Should not raise any exceptions
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(issue_dto)
            # Verify console methods were called
            assert mock_console.return_value.print.called

    def test_issue_presenter_render_with_minimal_issue_dto(self):
        """Test rendering a minimal IssueDTO."""
        issue_dto = IssueDTO.from_dict({
            "id": "issue456",
            "title": "Minimal Issue",
            "priority": "low",
            "status": "todo",
            "issue_type": "bug",
        })

        presenter = IssuePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(issue_dto)
            assert mock_console.return_value.print.called

    def test_issue_presenter_build_issue_header(self):
        """Test building issue header."""
        issue_dto = IssueDTO.from_dict({
            "id": "issue789",
            "title": "Header Test",
            "priority": "critical",
            "status": "blocked",
            "issue_type": "other",
        })

        presenter = IssuePresenter()
        header = presenter._build_issue_header(issue_dto)

        assert header is not None
        assert "issue789" in str(header)
        assert "Header Test" in str(header)
        assert "CRITICAL" in str(header)
        assert "BLOCKED" in str(header)

    def test_issue_presenter_build_metadata_table(self):
        """Test building metadata table."""
        issue_dto = IssueDTO.from_dict({
            "id": "issue001",
            "title": "Metadata Test",
            "priority": "high",
            "status": "in-progress",
            "issue_type": "feature",
            "assignee": "Bob",
            "milestone": "v2.0",
            "created": datetime.datetime(2024, 1, 1),
            "updated": datetime.datetime(2024, 1, 15),
            "labels": ["frontend", "docs"],
            "github_issue": 456,
        })

        presenter = IssuePresenter()
        table = presenter._build_metadata_table(issue_dto)

        assert table is not None

    def test_issue_presenter_build_timeline_table(self):
        """Test building timeline table."""
        issue_dto = IssueDTO.from_dict({
            "id": "issue002",
            "title": "Timeline Test",
            "priority": "medium",
            "status": "review",
            "issue_type": "feature",
            "estimated_hours": 8.5,
            "progress_percentage": 75,
            "actual_end_date": datetime.datetime(2024, 1, 10),
            "due_date": datetime.datetime(2024, 1, 20),
        })

        presenter = IssuePresenter()
        timeline = presenter._build_timeline_table(issue_dto)

        assert timeline is not None

    def test_issue_presenter_extract_description_and_criteria(self):
        """Test extracting description and acceptance criteria."""
        content = """# Issue Title

## Description
This is a test issue.
It has multiple lines.

## Acceptance Criteria
- Should pass tests
- Should be documented
"""
        presenter = IssuePresenter()
        description, acceptance = presenter._extract_description_and_criteria(content)

        assert "test issue" in description.lower()
        assert "pass tests" in acceptance.lower()

    def test_issue_presenter_extract_description_without_criteria(self):
        """Test extracting description when no criteria exists."""
        content = "Just a simple description without sections."
        presenter = IssuePresenter()
        description, acceptance = presenter._extract_description_and_criteria(content)

        assert description == content.strip()
        assert acceptance == ""


class TestMilestonePresenter:
    """Test suite for MilestonePresenter."""

    def test_milestone_presenter_init(self):
        """Test MilestonePresenter initialization."""
        presenter = MilestonePresenter()
        assert isinstance(presenter, MilestonePresenter)

    def test_milestone_presenter_has_render_method(self):
        """Test that MilestonePresenter implements render method."""
        presenter = MilestonePresenter()
        assert hasattr(presenter, "render")
        assert callable(presenter.render)

    def test_milestone_presenter_render_with_full_milestone_dto(self):
        """Test rendering a fully populated MilestoneDTO."""
        milestone_dto = MilestoneDTO.from_dict({
            "id": "milestone123",
            "name": "v1.0 Release",
            "status": "in-progress",
            "due_date": datetime.datetime(2024, 3, 1),
            "description": "First major release",
            "progress_percentage": 60,
            "issue_count": 20,
            "completed_count": 12,
            "created": datetime.datetime(2024, 1, 1),
            "updated": datetime.datetime(2024, 1, 15),
        })

        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(milestone_dto)
            assert mock_console.return_value.print.called

    def test_milestone_presenter_render_with_minimal_milestone_dto(self):
        """Test rendering a minimal MilestoneDTO."""
        milestone_dto = MilestoneDTO.from_dict({
            "id": "milestone456",
            "name": "v2.0",
            "status": "todo",
            "progress_percentage": 0,
            "issue_count": 0,
            "completed_count": 0,
        })

        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(milestone_dto)
            assert mock_console.return_value.print.called

    def test_milestone_presenter_build_header(self):
        """Test building milestone header."""
        milestone_dto = MilestoneDTO.from_dict({
            "id": "milestone789",
            "name": "Beta Release",
            "status": "blocked",
        })

        presenter = MilestonePresenter()
        header = presenter._build_milestone_header(milestone_dto)

        assert header is not None
        assert "Beta Release" in str(header)
        assert "BLOCKED" in str(header)

    def test_milestone_presenter_build_metadata_table(self):
        """Test building milestone metadata table."""
        milestone_dto = MilestoneDTO.from_dict({
            "id": "milestone001",
            "name": "Q1 Goals",
            "status": "in-progress",
            "due_date": datetime.datetime(2024, 3, 31),
            "description": "First quarter objectives",
            "progress_percentage": 45,
            "issue_count": 15,
            "completed_count": 7,
            "created": datetime.datetime(2024, 1, 1),
            "updated": datetime.datetime(2024, 1, 20),
        })

        presenter = MilestonePresenter()
        table = presenter._build_metadata_table(milestone_dto)

        assert table is not None


class TestProjectPresenter:
    """Test suite for ProjectPresenter."""

    def test_project_presenter_init(self):
        """Test ProjectPresenter initialization."""
        presenter = ProjectPresenter()
        assert isinstance(presenter, ProjectPresenter)

    def test_project_presenter_has_render_method(self):
        """Test that ProjectPresenter implements render method."""
        presenter = ProjectPresenter()
        assert hasattr(presenter, "render")
        assert callable(presenter.render)

    def test_project_presenter_render_with_full_project_dto(self):
        """Test rendering a fully populated ProjectDTO."""
        project_dto = ProjectDTO.from_dict({
            "id": "project123",
            "name": "Main App",
            "status": "active",
            "description": "Main application project",
            "owner": "Team A",
            "target_end_date": datetime.datetime(2024, 6, 30),
            "actual_end_date": None,
            "milestone_count": 5,
            "issue_count": 45,
            "created": datetime.datetime(2024, 1, 1),
            "updated": datetime.datetime(2024, 1, 20),
        })

        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(project_dto)
            assert mock_console.return_value.print.called

    def test_project_presenter_render_with_minimal_project_dto(self):
        """Test rendering a minimal ProjectDTO."""
        project_dto = ProjectDTO.from_dict({
            "id": "project456",
            "name": "Side Project",
            "status": "paused",
            "milestone_count": 0,
            "issue_count": 0,
        })

        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(project_dto)
            assert mock_console.return_value.print.called

    def test_project_presenter_build_header(self):
        """Test building project header."""
        project_dto = ProjectDTO.from_dict({
            "id": "project789",
            "name": "Experimental Feature",
            "status": "archived",
        })

        presenter = ProjectPresenter()
        header = presenter._build_project_header(project_dto)

        assert header is not None
        assert "Experimental Feature" in str(header)
        assert "ARCHIVED" in str(header)

    def test_project_presenter_build_metadata_table(self):
        """Test building project metadata table."""
        project_dto = ProjectDTO.from_dict({
            "id": "project001",
            "name": "Infrastructure",
            "status": "in-progress",
            "description": "Infrastructure improvements",
            "owner": "DevOps Team",
            "target_end_date": datetime.datetime(2024, 5, 31),
            "actual_end_date": datetime.datetime(2024, 5, 28),
            "milestone_count": 3,
            "issue_count": 20,
            "created": datetime.datetime(2023, 6, 1),
            "updated": datetime.datetime(2024, 1, 15),
        })

        presenter = ProjectPresenter()
        table = presenter._build_metadata_table(project_dto)

        assert table is not None
