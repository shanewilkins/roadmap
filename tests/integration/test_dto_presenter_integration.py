"""Integration tests for CLI DTO and Presenter flow."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.cli.dtos import IssueDTO, MilestoneDTO, ProjectDTO
from roadmap.adapters.cli.mappers import IssueMapper
from roadmap.adapters.cli.presentation.issue_presenter import IssuePresenter
from roadmap.adapters.cli.presentation.milestone_presenter import MilestonePresenter
from roadmap.adapters.cli.presentation.project_presenter import ProjectPresenter
from roadmap.common.constants import Priority, Status, IssueType
from roadmap.core.domain.issue import Issue


class TestIssueDTOPresenterIntegration:
    """Integration tests for Issue domain → DTO → Presenter flow."""

    def test_issue_domain_to_dto_to_presenter(self):
        """Test full flow: Issue domain model → DTO → Presenter."""
        # Create a mock domain Issue
        domain_issue = MagicMock(spec=Issue)
        domain_issue.id = "issue001"
        domain_issue.title = "Integration Test Issue"
        domain_issue.priority = Priority.HIGH
        domain_issue.status = Status.IN_PROGRESS
        domain_issue.issue_type = IssueType.FEATURE
        domain_issue.assignee = "Alice"
        domain_issue.milestone = "v1.0"
        domain_issue.due_date = datetime.datetime(2024, 3, 1)
        domain_issue.estimated_hours = 5.0
        domain_issue.actual_end_date = None
        domain_issue.progress_percentage = 50
        domain_issue.created = datetime.datetime(2024, 1, 1)
        domain_issue.updated = datetime.datetime(2024, 1, 15)
        domain_issue.content = "## Description\nTest feature\n\n## Acceptance Criteria\n- Works"
        domain_issue.labels = ["feature", "backend"]
        domain_issue.github_issue = 123

        # Step 1: Convert domain to DTO
        issue_dto = IssueMapper.domain_to_dto(domain_issue)

        # Verify DTO is created correctly
        assert isinstance(issue_dto, IssueDTO)
        assert issue_dto.id == "issue001"
        assert issue_dto.title == "Integration Test Issue"
        assert issue_dto.priority == "high"  # Enum converted to string
        assert issue_dto.status == "in-progress"
        assert issue_dto.issue_type == "feature"
        assert issue_dto.assignee == "Alice"

        # Step 2: Render DTO with presenter
        presenter = IssuePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(issue_dto)
            # Verify console methods were called (rendering happened)
            assert mock_console.return_value.print.called

    def test_issue_roundtrip_conversion(self):
        """Test domain → DTO → domain roundtrip conversion."""
        # Create domain issue
        domain_issue = MagicMock(spec=Issue)
        domain_issue.id = "issue002"
        domain_issue.title = "Roundtrip Test"
        domain_issue.priority = Priority.MEDIUM
        domain_issue.status = Status.TODO
        domain_issue.issue_type = IssueType.BUG
        domain_issue.assignee = None
        domain_issue.milestone = None
        domain_issue.due_date = None
        domain_issue.estimated_hours = None
        domain_issue.actual_end_date = None
        domain_issue.progress_percentage = 0
        domain_issue.created = datetime.datetime(2024, 1, 1)
        domain_issue.updated = datetime.datetime(2024, 1, 1)
        domain_issue.content = None
        domain_issue.labels = []
        domain_issue.github_issue = None

        # Convert to DTO
        issue_dto = IssueMapper.domain_to_dto(domain_issue)

        # Convert back to domain
        converted_back = IssueMapper.dto_to_domain(issue_dto)

        # Verify key fields survived roundtrip
        assert converted_back.id == domain_issue.id
        assert converted_back.title == domain_issue.title
        assert converted_back.priority == domain_issue.priority
        assert converted_back.status == domain_issue.status


class TestMilestoneDTOPresenterIntegration:
    """Integration tests for Milestone DTO and Presenter (without domain conversion)."""

    def test_milestone_dto_to_presenter(self):
        """Test Milestone DTO → Presenter rendering."""
        # Create DTO directly (no domain conversion needed for this test)
        milestone_dto = MilestoneDTO.from_dict({
            "id": "milestone001",
            "name": "Q1 2024",
            "status": "active",
            "due_date": datetime.datetime(2024, 3, 31),
            "description": "First quarter goals",
            "progress_percentage": 60,
            "issue_count": 20,
            "completed_count": 12,
            "created": datetime.datetime(2024, 1, 1),
            "updated": datetime.datetime(2024, 1, 20),
        })

        # Render DTO with presenter
        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(milestone_dto)
            assert mock_console.return_value.print.called


class TestProjectDTOPresenterIntegration:
    """Integration tests for Project DTO and Presenter (without domain conversion)."""

    def test_project_dto_to_presenter(self):
        """Test Project DTO → Presenter rendering."""
        # Create DTO directly (no domain conversion needed for this test)
        project_dto = ProjectDTO.from_dict({
            "id": "project001",
            "name": "Main Application",
            "status": "active",
            "description": "Core application",
            "owner": "Team A",
            "target_end_date": datetime.datetime(2024, 6, 30),
            "actual_end_date": None,
            "milestone_count": 4,
            "issue_count": 50,
            "created": datetime.datetime(2024, 1, 1),
            "updated": datetime.datetime(2024, 1, 15),
        })

        # Render DTO with presenter
        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(project_dto)
            assert mock_console.return_value.print.called


class TestListCommandDTOFlow:
    """Integration tests for list command using DTOs."""

    def test_list_command_issue_dto_conversion(self):
        """Test that list command properly converts domain issues to DTOs."""
        # Create mock domain issues
        domain_issues = []
        for i in range(3):
            issue = MagicMock(spec=Issue)
            issue.id = f"issue{i:03d}"
            issue.title = f"Test Issue {i}"
            issue.priority = Priority.HIGH if i % 2 == 0 else Priority.LOW
            issue.status = Status.TODO
            issue.issue_type = IssueType.FEATURE
            issue.assignee = "Alice" if i % 2 == 0 else None
            issue.milestone = "v1.0" if i % 2 == 0 else None
            issue.due_date = None
            issue.estimated_hours = 5.0
            issue.actual_end_date = None
            issue.progress_percentage = 0
            issue.created = datetime.datetime(2024, 1, 1)
            issue.updated = datetime.datetime(2024, 1, 1)
            issue.content = None
            issue.labels = []
            issue.github_issue = None
            domain_issues.append(issue)

        # Convert to DTOs (as list command does)
        issue_dtos = [IssueMapper.domain_to_dto(issue) for issue in domain_issues]

        # Verify DTOs
        assert len(issue_dtos) == 3
        assert all(isinstance(dto, IssueDTO) for dto in issue_dtos)
        assert issue_dtos[0].title == "Test Issue 0"
        assert issue_dtos[1].title == "Test Issue 1"
        assert issue_dtos[2].title == "Test Issue 2"

        # Verify enum conversion to strings
        assert issue_dtos[0].priority == "high"
        assert issue_dtos[1].priority == "low"

    def test_mixed_entity_dto_rendering(self):
        """Test rendering different entity types as DTOs."""
        # Create issue DTO
        issue_dto = IssueDTO.from_dict({
            "id": "i1",
            "title": "Issue",
            "priority": "critical",
            "status": "blocked",
            "issue_type": "bug",
        })

        # Create milestone DTO
        milestone_dto = MilestoneDTO.from_dict({
            "id": "m1",
            "name": "Milestone",
            "status": "active",
            "progress_percentage": 0,
            "issue_count": 0,
            "completed_count": 0,
        })

        # Create project DTO
        project_dto = ProjectDTO.from_dict({
            "id": "p1",
            "name": "Project",
            "status": "active",
            "milestone_count": 0,
            "issue_count": 0,
        })

        # Verify all DTOs were created correctly
        assert isinstance(issue_dto, IssueDTO)
        assert issue_dto.priority == "critical"
        assert issue_dto.status == "blocked"

        assert isinstance(milestone_dto, MilestoneDTO)
        assert milestone_dto.name == "Milestone"

        assert isinstance(project_dto, ProjectDTO)
        assert project_dto.name == "Project"
