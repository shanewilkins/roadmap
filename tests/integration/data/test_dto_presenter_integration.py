"""Integration tests for CLI DTO and Presenter flow."""

import datetime
from unittest.mock import patch

from roadmap.adapters.cli.dtos import IssueDTO
from roadmap.adapters.cli.mappers import IssueMapper
from roadmap.adapters.cli.presentation.issue_presenter import IssuePresenter
from roadmap.adapters.cli.presentation.milestone_presenter import MilestonePresenter
from roadmap.adapters.cli.presentation.project_presenter import ProjectPresenter
from roadmap.common.constants import IssueType, Priority, Status


class TestIssueDTOPresenterIntegration:
    """Integration tests for Issue domain → DTO → Presenter flow."""

    def test_issue_domain_to_dto_to_presenter(self, mock_issue_factory):
        """Test full flow: Issue domain model → DTO → Presenter."""
        # Create a mock domain Issue
        domain_issue = mock_issue_factory(
            id="issue001",
            title="Integration Test Issue",
            headline="Test issue headline",
            priority=Priority.HIGH,
            status=Status.IN_PROGRESS,
            issue_type=IssueType.FEATURE,
            assignee="Alice",
            milestone="v1-0",
            due_date=datetime.datetime(2024, 3, 1),
            estimated_hours=5.0,
            actual_end_date=None,
            progress_percentage=50,
            created=datetime.datetime(2024, 1, 1),
            updated=datetime.datetime(2024, 1, 15),
            content="## Description\nTest feature\n\n## Acceptance Criteria\n- Works",
            labels=["feature", "backend"],
            github_issue=123,
        )

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

    def test_issue_roundtrip_conversion(self, mock_issue_factory):
        """Test domain → DTO → domain roundtrip conversion."""
        # Create domain issue
        domain_issue = mock_issue_factory(
            id="issue002",
            title="Roundtrip Test",
            headline="Roundtrip test headline",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            issue_type=IssueType.BUG,
            assignee=None,
            milestone=None,
            due_date=None,
            estimated_hours=None,
            actual_end_date=None,
            progress_percentage=0,
            created=datetime.datetime(2024, 1, 1),
            updated=datetime.datetime(2024, 1, 1),
            content=None,
            labels=[],
            github_issue=None,
        )

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

    def test_milestone_dto_to_presenter(self, milestone_dto):
        """Test Milestone DTO → Presenter rendering."""
        # Render DTO with presenter
        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(milestone_dto)
            assert mock_console.return_value.print.called


class TestProjectDTOPresenterIntegration:
    """Integration tests for Project DTO and Presenter (without domain conversion)."""

    def test_project_dto_to_presenter(self, project_dto):
        """Test Project DTO → Presenter rendering."""
        # Render DTO with presenter
        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(project_dto)
            assert mock_console.return_value.print.called


class TestListCommandDTOFlow:
    """Integration tests for list command using DTOs."""

    def test_list_command_issue_dto_conversion(self, mock_issue_factory):
        """Test that list command properly converts domain issues to DTOs."""
        # Create mock domain issues
        domain_issues = []
        for i in range(3):
            issue = mock_issue_factory(
                id=f"issue{i:03d}",
                title=f"Test Issue {i}",
                headline=f"Headline for issue {i}",
                priority=Priority.HIGH if i % 2 == 0 else Priority.LOW,
                status=Status.TODO,
                issue_type=IssueType.FEATURE,
                assignee="Alice" if i % 2 == 0 else None,
                milestone="v1-0" if i % 2 == 0 else None,
                due_date=None,
                estimated_hours=5.0,
                actual_end_date=None,
                progress_percentage=0,
                created=datetime.datetime(2024, 1, 1),
                updated=datetime.datetime(2024, 1, 1),
                content=None,
                labels=[],
                github_issue=None,
            )
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

    def test_mixed_entity_dto_rendering(self, milestone_dto, project_dto):
        """Test rendering different entity types as DTOs."""
        # Create issue DTO
        issue_dto = IssueDTO.from_dict(
            {
                "id": "i1",
                "title": "Issue",
                "priority": "critical",
                "status": "blocked",
                "issue_type": "bug",
            }
        )

        # Verify all DTOs were created correctly
        assert isinstance(issue_dto, IssueDTO)
        assert issue_dto.priority == "critical"
        assert issue_dto.status == "blocked"

        assert isinstance(milestone_dto, type(milestone_dto))
        assert milestone_dto.name == "v1-0-0"

        assert isinstance(project_dto, type(project_dto))
        assert project_dto.name == "Website Redesign"
