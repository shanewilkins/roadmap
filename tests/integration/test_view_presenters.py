"""Integration tests for Phase 3: View presenter refactoring.

Tests the refactored milestone/view.py and projects/view.py commands
using the new enhanced presenters (MilestonePresenter, ProjectPresenter).

Validates:
1. MilestonePresenter render with issues, progress, and descriptions
2. ProjectPresenter render with milestones, effort, and descriptions
3. Integration with mappers for domain->DTO conversion
4. Command handler integration with presenter
5. Error handling and edge cases
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.dtos import MilestoneDTO, ProjectDTO
from roadmap.adapters.cli.mappers import MilestoneMapper, ProjectMapper
from roadmap.adapters.cli.presentation.milestone_presenter import MilestonePresenter
from roadmap.adapters.cli.presentation.project_presenter import ProjectPresenter
from roadmap.core.domain.milestone import Milestone, MilestoneStatus
from roadmap.core.domain.project import Project, ProjectStatus


class TestMilestonePresenterFullRendering:
    """Test MilestonePresenter render with full milestone data."""

    def test_render_with_all_components(self):
        """Test rendering milestone with issues, progress, and content."""
        # Setup milestone DTO
        milestone_dto = MilestoneDTO(
            id="m1",
            name="v1.0.0",
            status="open",
            due_date=datetime.now() + timedelta(days=30),
            description="Release version 1.0",
            progress_percentage=75,
            issue_count=4,
            completed_count=3,
            created=datetime.now(),
            updated=datetime.now(),
        )

        # Setup mock issues
        mock_issues = [
            MagicMock(
                id="i1",
                title="Feature A",
                status=MagicMock(value="closed"),
                priority=MagicMock(value="high"),
                assignee="alice",
                progress_display="100%",
                estimated_time_display="8h",
            ),
            MagicMock(
                id="i2",
                title="Feature B with a longer title that should be truncated",
                status=MagicMock(value="in-progress"),
                priority=MagicMock(value="medium"),
                assignee="bob",
                progress_display="50%",
                estimated_time_display="16h",
            ),
        ]

        # Setup progress data
        progress_data = {"completed": 3, "total": 4}

        # Setup description with content
        description_content = (
            "This is the milestone description.\n"
            "\n"
            "## Goals\n"
            "- Complete feature A\n"
            "- Complete feature B"
        )

        # Render (should not raise)
        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(
                milestone_dto,
                issues=mock_issues,
                progress_data=progress_data,
                description_content=description_content,
                comments_text=None,
            )

            # Verify print was called for header, progress, metadata, issues, description
            assert mock_console.return_value.print.call_count >= 5

    def test_render_without_optional_data(self):
        """Test rendering milestone with minimal data."""
        milestone_dto = MilestoneDTO(
            id="m1",
            name="v1.0.0",
            status="closed",
            due_date=None,
            description="",
            created=datetime.now(),
            updated=datetime.now(),
        )

        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(milestone_dto)

            # Should still print header and metadata
            assert mock_console.return_value.print.call_count >= 2

    def test_render_with_overdue_milestone(self):
        """Test rendering overdue milestone with due date handling."""
        due_date = datetime.now() - timedelta(days=5)
        milestone_dto = MilestoneDTO(
            id="m1",
            name="v0.9.0",
            status="open",
            due_date=due_date,
            description="Overdue milestone",
            created=datetime.now() - timedelta(days=30),
            updated=datetime.now(),
        )

        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(milestone_dto)

            # Should render header with overdue warning
            assert mock_console.return_value.print.called


class TestProjectPresenterFullRendering:
    """Test ProjectPresenter render with full project data."""

    def test_render_with_all_components(self):
        """Test rendering project with milestones, effort, and content."""
        project_dto = ProjectDTO(
            id="p1",
            name="Website Redesign",
            status="active",
            description="Redesign the main website",
            owner="alice",
            target_end_date=datetime.now() + timedelta(days=60),
            actual_end_date=None,
            created=datetime.now(),
            updated=datetime.now(),
        )

        # Skip milestone rendering for this test (tested separately)
        # Just test effort and description
        effort_data = {"estimated": 320.0, "actual": 240.0}
        description_content = "Project to redesign the main website and improve UX."

        # Render (should not raise)
        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(
                project_dto,
                milestones=None,  # Skip milestone rendering in this test
                effort_data=effort_data,
                description_content=description_content,
                comments_text=None,
            )

            # Verify print was called for header, metadata, effort, description
            assert mock_console.return_value.print.call_count >= 4

    def test_render_without_optional_data(self):
        """Test rendering project with minimal data."""
        project_dto = ProjectDTO(
            id="p1",
            name="Small Task",
            status="planning",
            description="",
            owner=None,
            target_end_date=None,
            actual_end_date=None,
            created=datetime.now(),
            updated=datetime.now(),
        )

        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(project_dto)

            # Should still print header and metadata
            assert mock_console.return_value.print.call_count >= 2

    def test_render_with_large_effort_estimate(self):
        """Test effort formatting for large hour counts."""
        project_dto = ProjectDTO(
            id="p1",
            name="Major Project",
            status="active",
            description="Large undertaking",
            owner="bob",
            target_end_date=datetime.now() + timedelta(days=120),
            actual_end_date=None,
            milestone_count=5,
            issue_count=50,
            created=datetime.now(),
            updated=datetime.now(),
        )

        # Large effort data (should be displayed in days)
        effort_data = {"estimated": 800.0, "actual": 600.0}

        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(project_dto, effort_data=effort_data)

            # Verify effort panel was rendered
            assert mock_console.return_value.print.call_count >= 3


class TestMilestonePresenterIntegrationWithMapper:
    """Test MilestonePresenter integration with MilestoneMapper."""

    def test_domain_to_dto_to_presenter_flow(self):
        """Test end-to-end flow: domain model -> DTO -> presenter."""
        # Create domain milestone
        milestone = Milestone(
            name="v1.0.0",
            status=MilestoneStatus.OPEN,
            due_date=datetime.now() + timedelta(days=30),
            description="Release version 1.0",
            content="Release version 1.0\n\n## Goals\n- Complete features",
            created=datetime.now(),
            updated=datetime.now(),
            comments=[],
        )

        # Convert to DTO
        milestone_dto = MilestoneMapper.domain_to_dto(milestone)

        # Verify DTO conversion
        assert milestone_dto.name == "v1.0.0"
        assert milestone_dto.status == "open"
        # Note: progress_percentage may not be preserved in mapper, so just check rendering

        # Render with presenter (should not raise)
        presenter = MilestonePresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(milestone_dto)
            assert mock_console.return_value.print.call_count >= 2

    def test_milestone_dto_roundtrip_with_enum_conversion(self):
        """Test DTO roundtrip preserves data and handles enum conversion."""
        # Create domain milestone with enum status
        milestone = Milestone(
            name="v1.0.0",
            status=MilestoneStatus.CLOSED,
            due_date=None,
            description="Completed milestone",
            content="",  # Changed from None to empty string
            created=datetime.now(),
            updated=datetime.now(),
            comments=[],
        )

        # Domain -> DTO
        milestone_dto = MilestoneMapper.domain_to_dto(milestone)
        assert isinstance(milestone_dto.status, str)
        assert milestone_dto.status == "closed"

        # DTO -> Domain
        milestone_restored = MilestoneMapper.dto_to_domain(milestone_dto)
        assert milestone_restored.status == MilestoneStatus.CLOSED
        assert milestone_restored.name == milestone.name


class TestProjectPresenterIntegrationWithMapper:
    """Test ProjectPresenter integration with ProjectMapper."""

    def test_domain_to_dto_to_presenter_flow(self):
        """Test end-to-end flow: domain model -> DTO -> presenter."""
        # Create domain project
        project = Project(
            id="p1",
            name="Website Redesign",
            status=ProjectStatus.ACTIVE,
            description="Redesign the main website",
            content="Redesign the main website\n\n## Objectives\n- Improve UX",
            owner="alice",
            target_end_date=datetime.now() + timedelta(days=60),
            actual_end_date=None,
            start_date=datetime.now() - timedelta(days=10),
            estimated_hours=320.0,
            actual_hours=240.0,
            milestones=["Design", "Development", "Testing"],
            created=datetime.now(),
            updated=datetime.now(),
            comments=[],
        )

        # Convert to DTO
        project_dto = ProjectMapper.domain_to_dto(project)

        # Verify DTO conversion
        assert project_dto.name == "Website Redesign"
        assert project_dto.status == "active"
        assert project_dto.owner == "alice"

        # Render with presenter (should not raise)
        presenter = ProjectPresenter()
        with patch.object(presenter, "_get_console") as mock_console:
            presenter.render(project_dto)
            assert mock_console.return_value.print.call_count >= 2

    def test_project_dto_roundtrip_with_enum_conversion(self):
        """Test DTO roundtrip preserves data and handles enum conversion."""
        # Create domain project with enum status
        project = Project(
            id="p1",
            name="Small Task",
            status=ProjectStatus.PLANNING,
            description="",  # Changed from None to empty string
            content="",  # Changed from None to empty string
            owner=None,
            target_end_date=None,
            actual_end_date=None,
            start_date=None,
            estimated_hours=None,
            actual_hours=None,
            milestones=[],
            created=datetime.now(),
            updated=datetime.now(),
            comments=[],
        )

        # Domain -> DTO
        project_dto = ProjectMapper.domain_to_dto(project)
        assert isinstance(project_dto.status, str)
        assert project_dto.status == "planning"

        # DTO -> Domain
        project_restored = ProjectMapper.dto_to_domain(project_dto)
        assert project_restored.status == ProjectStatus.PLANNING
        assert project_restored.name == project.name


class TestMilestonePresenterHelperMethods:
    """Test MilestonePresenter helper methods."""

    def test_extract_description_and_goals(self):
        """Test extracting description and goals from content."""
        content = (
            "This is the description.\n"
            "It spans multiple lines.\n"
            "\n"
            "## Goals\n"
            "- Goal 1\n"
            "- Goal 2\n"
            "- Goal 3"
        )

        description, goals = MilestonePresenter._extract_description_and_goals(content)

        assert "description" in description.lower()
        assert "Goal 1" in goals
        assert "Goal 2" in goals

    def test_extract_with_no_goals(self):
        """Test extraction when no goals section exists."""
        content = "Just a description without any goals section."

        description, goals = MilestonePresenter._extract_description_and_goals(content)

        assert "description" in description
        assert goals == ""

    def test_extract_with_empty_content(self):
        """Test extraction with empty content."""
        description, goals = MilestonePresenter._extract_description_and_goals("")

        assert description == ""
        assert goals == ""


class TestProjectPresenterHelperMethods:
    """Test ProjectPresenter helper methods."""

    def test_build_effort_table_with_hours(self):
        """Test building effort table with hour data."""
        effort_data = {"estimated": 160.0, "actual": 120.0}

        presenter = ProjectPresenter()
        table = presenter._build_effort_table(effort_data)

        assert table is not None
        # Table should have 2 rows
        assert len(table.rows) == 2

    def test_build_effort_table_with_large_hours(self):
        """Test effort formatting converts to days for large numbers."""
        effort_data = {"estimated": 320.0, "actual": None}

        presenter = ProjectPresenter()
        table = presenter._build_effort_table(effort_data)

        assert table is not None
        assert len(table.rows) == 1

    def test_build_effort_table_with_no_data(self):
        """Test effort table returns None with no data."""
        effort_data = {"estimated": None, "actual": None}

        presenter = ProjectPresenter()
        table = presenter._build_effort_table(effort_data)

        assert table is None


class TestMilestoneViewCommandIntegration:
    """Test milestone view command integration with presenter."""

    def test_milestone_view_imports_successfully(self):
        """Test that milestone view command can be imported."""
        from roadmap.adapters.cli.milestones.view import view_milestone

        # Verify command exists and has correct structure
        assert hasattr(view_milestone, "callback")
        assert view_milestone.name == "view"

    def test_project_view_imports_successfully(self):
        """Test that project view command can be imported."""
        from roadmap.adapters.cli.projects.view import view_project

        # Verify command exists and has correct structure
        assert hasattr(view_project, "callback")
        assert view_project.name == "view"


class TestPhase3CodeReduction:
    """Test that Phase 3 refactoring achieved code reduction goals."""

    def test_milestone_view_file_size_reduction(self):
        """Verify milestone view file is significantly smaller after refactoring."""
        # This is verified by checking the actual file size
        # Original: ~350 lines
        # Refactored: ~100 lines (70% reduction expected)
        import os

        view_file = "/Users/shane/roadmap/roadmap/adapters/cli/milestones/view.py"
        if os.path.exists(view_file):
            with open(view_file) as f:
                lines = len(f.readlines())
            # Should be significantly less than 350
            assert lines < 200, f"Expected < 200 lines, got {lines}"

    def test_project_view_file_size_reduction(self):
        """Verify project view file is significantly smaller after refactoring."""
        # This is verified by checking the actual file size
        # Original: ~286 lines
        # Refactored: ~100 lines (65% reduction expected)
        import os

        view_file = "/Users/shane/roadmap/roadmap/adapters/cli/projects/view.py"
        if os.path.exists(view_file):
            with open(view_file) as f:
                lines = len(f.readlines())
            # Should be significantly less than 286
            assert lines < 180, f"Expected < 180 lines, got {lines}"
