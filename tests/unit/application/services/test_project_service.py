"""Unit tests for ProjectService - project operations and management."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from roadmap.core.domain.milestone import MilestoneStatus
from roadmap.core.domain.project import Project, ProjectStatus
from roadmap.core.services.project_service import ProjectService


@pytest.fixture
def mock_db():
    """Create a mock StateManager."""
    return Mock()


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for projects and milestones."""
    projects_dir = tmp_path / "projects"
    milestones_dir = tmp_path / "milestones"
    projects_dir.mkdir()
    milestones_dir.mkdir()
    return {"projects": projects_dir, "milestones": milestones_dir}


@pytest.fixture
def project_service(mock_db, temp_dirs):
    """Create a ProjectService instance with temp directories."""
    return ProjectService(
        db=mock_db,
        projects_dir=temp_dirs["projects"],
        milestones_dir=temp_dirs["milestones"],
    )


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id="PROJ-001",
        name="Test Project",
        description="A test project",
        status=ProjectStatus.ACTIVE,
        created=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        updated=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        milestones=["Milestone 1", "Milestone 2"],
        content="# Test Project\n\nProject content",
    )


class TestProjectServiceInit:
    """Test ProjectService initialization."""

    def test_init_sets_dependencies(self, mock_db, temp_dirs):
        """Test initialization sets all dependencies correctly."""
        service = ProjectService(
            db=mock_db,
            projects_dir=temp_dirs["projects"],
            milestones_dir=temp_dirs["milestones"],
        )

        assert service.db == mock_db
        assert service.projects_dir == temp_dirs["projects"]
        assert service.milestones_dir == temp_dirs["milestones"]


class TestProjectServiceList:
    """Test project listing functionality."""

    def test_list_projects_empty(self, project_service):
        """Test listing projects when none exist."""
        projects = project_service.list_projects()

        assert projects == []

    def test_list_projects_returns_all(
        self, project_service, temp_dirs, sample_project
    ):
        """Test listing returns all project files."""
        # Create project files
        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            return_value=sample_project,
        ):
            # Create dummy files
            (temp_dirs["projects"] / "project1.md").touch()
            (temp_dirs["projects"] / "project2.md").touch()

            projects = project_service.list_projects()

            assert len(projects) == 2

    def test_list_projects_sorted_by_created(
        self, project_service, temp_dirs, sample_project
    ):
        """Test projects are sorted by creation date."""
        # Create two projects with different creation dates
        project1 = Project(
            id="PROJ-001",
            name="Project 1",
            created=datetime(2025, 1, 2, tzinfo=timezone.utc),
            content="",
        )
        project2 = Project(
            id="PROJ-002",
            name="Project 2",
            created=datetime(2025, 1, 1, tzinfo=timezone.utc),
            content="",
        )

        (temp_dirs["projects"] / "project1.md").touch()
        (temp_dirs["projects"] / "project2.md").touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            side_effect=[project1, project2],
        ):
            projects = project_service.list_projects()

            # Should be sorted by created date (oldest first)
            assert projects[0].id == "PROJ-002"
            assert projects[1].id == "PROJ-001"

    def test_list_projects_skips_invalid_files(self, project_service, temp_dirs):
        """Test listing skips files that can't be parsed."""
        # Create dummy file
        (temp_dirs["projects"] / "invalid.md").touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            side_effect=Exception("Parse error"),
        ):
            projects = project_service.list_projects()

            # Should return empty list, not raise exception
            assert projects == []


class TestProjectServiceGet:
    """Test getting individual projects."""

    def test_get_project_found(self, project_service, temp_dirs, sample_project):
        """Test getting an existing project."""
        (temp_dirs["projects"] / "project.md").touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            return_value=sample_project,
        ):
            project = project_service.get_project("PROJ-001")

            assert project is not None
            assert project.id == "PROJ-001"
            assert project.name == "Test Project"

    def test_get_project_not_found(self, project_service):
        """Test getting a non-existent project returns None."""
        project = project_service.get_project("NONEXISTENT")

        assert project is None

    def test_get_project_partial_id_match(
        self, project_service, temp_dirs, sample_project
    ):
        """Test getting project with partial ID match."""
        (temp_dirs["projects"] / "project.md").touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            return_value=sample_project,
        ):
            # Should match with partial ID
            project = project_service.get_project("PROJ")

            assert project is not None
            assert project.id == "PROJ-001"

    def test_get_project_skips_invalid_files(self, project_service, temp_dirs):
        """Test get_project skips files that can't be parsed."""
        (temp_dirs["projects"] / "invalid.md").touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            side_effect=Exception("Parse error"),
        ):
            project = project_service.get_project("PROJ-001")

            # Should return None, not raise exception
            assert project is None


class TestProjectServiceSave:
    """Test saving projects."""

    def test_save_project_existing(self, project_service, temp_dirs, sample_project):
        """Test saving an existing project updates the file."""
        project_file = temp_dirs["projects"] / "project.md"
        project_file.touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=sample_project,
            ),
            patch(
                "roadmap.core.services.project_service.ProjectParser.save_project_file"
            ) as mock_save,
            patch("roadmap.core.services.project_service.now_utc") as mock_now,
        ):
            mock_now.return_value = datetime(2025, 1, 20, tzinfo=timezone.utc)

            result = project_service.save_project(sample_project)

            assert result is True
            mock_save.assert_called_once()
            # Check updated timestamp was set
            assert sample_project.updated == datetime(2025, 1, 20, tzinfo=timezone.utc)

    def test_save_project_new(self, project_service, temp_dirs, sample_project):
        """Test saving a new project creates a file."""
        # No existing files

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.save_project_file"
            ) as mock_save,
            patch("roadmap.core.services.project_service.now_utc") as mock_now,
        ):
            mock_now.return_value = datetime(2025, 1, 20, tzinfo=timezone.utc)

            result = project_service.save_project(sample_project)

            assert result is True
            mock_save.assert_called_once()
            # Should save to expected path
            expected_path = temp_dirs["projects"] / sample_project.filename
            mock_save.assert_called_with(sample_project, expected_path)

    def test_save_project_handles_parse_errors(
        self, project_service, temp_dirs, sample_project
    ):
        """Test save_project handles parse errors gracefully."""
        project_file = temp_dirs["projects"] / "project.md"
        project_file.touch()

        # Parse error means it won't find existing file, will save as new
        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                side_effect=Exception("Parse error"),
            ),
            patch(
                "roadmap.core.services.project_service.ProjectParser.save_project_file"
            ) as mock_save,
            patch("roadmap.core.services.project_service.now_utc"),
        ):
            result = project_service.save_project(sample_project)

            # Should still save (as new file)
            assert result is True
            mock_save.assert_called_once()


class TestProjectServiceCreate:
    """Test project creation."""

    def test_create_project_minimal(self, project_service):
        """Test creating a project with minimal parameters."""
        with patch.object(project_service, "save_project", return_value=True):
            project = project_service.create_project(name="New Project")

            assert project.name == "New Project"
            assert project.description == ""
            assert project.milestones == []

    def test_create_project_full(self, project_service):
        """Test creating a project with all parameters."""
        with patch.object(project_service, "save_project", return_value=True):
            project = project_service.create_project(
                name="New Project",
                description="Project description",
                milestones=["M1", "M2"],
            )

            assert project.name == "New Project"
            assert project.description == "Project description"
            assert project.milestones == ["M1", "M2"]

    def test_create_project_calls_save(self, project_service):
        """Test creating a project calls save_project."""
        with patch.object(
            project_service, "save_project", return_value=True
        ) as mock_save:
            project = project_service.create_project(name="New Project")

            mock_save.assert_called_once_with(project)

    def test_create_project_generates_content(self, project_service):
        """Test created project has generated content."""
        with patch.object(project_service, "save_project", return_value=True):
            project = project_service.create_project(
                name="New Project", description="Test description"
            )

            assert "# New Project" in project.content
            assert "Test description" in project.content


class TestProjectServiceUpdate:
    """Test project updates."""

    def test_update_project_success(self, project_service, temp_dirs, sample_project):
        """Test updating a project successfully."""
        (temp_dirs["projects"] / "project.md").touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=sample_project,
            ),
            patch.object(project_service, "save_project", return_value=True),
        ):
            updated = project_service.update_project(
                "PROJ-001", name="Updated Name", description="Updated Description"
            )

            assert updated is not None
            assert updated.name == "Updated Name"
            assert updated.description == "Updated Description"

    def test_update_project_not_found(self, project_service):
        """Test updating a non-existent project returns None."""
        result = project_service.update_project("NONEXISTENT", name="New Name")

        assert result is None

    def test_update_project_calls_save(
        self, project_service, temp_dirs, sample_project
    ):
        """Test update_project calls save_project."""
        (temp_dirs["projects"] / "project.md").touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=sample_project,
            ),
            patch.object(
                project_service, "save_project", return_value=True
            ) as mock_save,
        ):
            project_service.update_project("PROJ-001", name="Updated")

            mock_save.assert_called_once()

    def test_update_project_ignores_invalid_fields(
        self, project_service, temp_dirs, sample_project
    ):
        """Test updating with invalid field names is handled."""
        (temp_dirs["projects"] / "project.md").touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=sample_project,
            ),
            patch.object(project_service, "save_project", return_value=True),
        ):
            # Should not raise exception for invalid field
            updated = project_service.update_project(
                "PROJ-001", nonexistent_field="value"
            )

            assert updated is not None


class TestProjectServiceDelete:
    """Test project deletion."""

    def test_delete_project_success(self, project_service, temp_dirs, sample_project):
        """Test deleting an existing project."""
        project_file = temp_dirs["projects"] / "project.md"
        project_file.touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            return_value=sample_project,
        ):
            result = project_service.delete_project("PROJ-001")

            assert result is True
            assert not project_file.exists()

    def test_delete_project_not_found(self, project_service):
        """Test deleting a non-existent project returns False."""
        result = project_service.delete_project("NONEXISTENT")

        assert result is False

    def test_delete_project_partial_id(
        self, project_service, temp_dirs, sample_project
    ):
        """Test deleting with partial ID match."""
        project_file = temp_dirs["projects"] / "project.md"
        project_file.touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            return_value=sample_project,
        ):
            result = project_service.delete_project("PROJ")

            assert result is True
            assert not project_file.exists()

    def test_delete_project_skips_invalid_files(self, project_service, temp_dirs):
        """Test delete_project skips files that can't be parsed."""
        (temp_dirs["projects"] / "invalid.md").touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            side_effect=Exception("Parse error"),
        ):
            result = project_service.delete_project("PROJ-001")

            # Should return False, not raise exception
            assert result is False


class TestProjectServiceProgress:
    """Test progress calculation."""

    def test_calculate_progress_no_project(self, project_service):
        """Test calculating progress for non-existent project."""
        progress = project_service.calculate_progress("NONEXISTENT")

        assert progress["total_milestones"] == 0
        assert progress["completed_milestones"] == 0
        assert progress["progress"] == 0.0
        assert progress["milestone_status"] == {}

    def test_calculate_progress_no_milestones(
        self, project_service, temp_dirs, sample_project
    ):
        """Test calculating progress for project with no milestones."""
        project_without_milestones = Project(
            id="PROJ-002",
            name="No Milestones",
            milestones=[],
            content="",
        )
        (temp_dirs["projects"] / "project.md").touch()

        with patch(
            "roadmap.core.services.project_service.ProjectParser.parse_project_file",
            return_value=project_without_milestones,
        ):
            progress = project_service.calculate_progress("PROJ-002")

            assert progress["total_milestones"] == 0
            assert progress["progress"] == 0.0

    def test_calculate_progress_all_completed(self, project_service, temp_dirs):
        """Test progress calculation with all milestones completed."""
        from roadmap.core.domain.milestone import Milestone

        # Create project with 2 milestones
        project = Project(
            id="PROJ-001",
            name="Test",
            milestones=["Milestone 1", "Milestone 2"],
            content="",
        )

        # Create completed milestones
        milestone1 = Milestone(
            name="Milestone 1", status=MilestoneStatus.CLOSED, content=""
        )
        milestone2 = Milestone(
            name="Milestone 2", status=MilestoneStatus.CLOSED, content=""
        )

        (temp_dirs["projects"] / "project.md").touch()
        (temp_dirs["milestones"] / "m1.md").touch()
        (temp_dirs["milestones"] / "m2.md").touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=project,
            ),
            patch(
                "roadmap.core.services.project_service.MilestoneParser.parse_milestone_file",
                side_effect=[milestone1, milestone2],
            ),
        ):
            progress = project_service.calculate_progress("PROJ-001")

            assert progress["total_milestones"] == 2
            assert progress["completed_milestones"] == 2
            assert progress["progress"] == 100.0
            assert progress["milestone_status"]["Milestone 1"] == "closed"
            assert progress["milestone_status"]["Milestone 2"] == "closed"

    def test_calculate_progress_partial(self, project_service, temp_dirs):
        """Test progress calculation with partial completion."""
        from roadmap.core.domain.milestone import Milestone

        project = Project(
            id="PROJ-001",
            name="Test",
            milestones=["Milestone 1", "Milestone 2"],
            content="",
        )

        # One closed, one active
        milestone1 = Milestone(
            name="Milestone 1", status=MilestoneStatus.CLOSED, content=""
        )
        milestone2 = Milestone(
            name="Milestone 2", status=MilestoneStatus.OPEN, content=""
        )

        (temp_dirs["projects"] / "project.md").touch()
        (temp_dirs["milestones"] / "m1.md").touch()
        (temp_dirs["milestones"] / "m2.md").touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=project,
            ),
            patch(
                "roadmap.core.services.project_service.MilestoneParser.parse_milestone_file",
                side_effect=[milestone1, milestone2],
            ),
        ):
            progress = project_service.calculate_progress("PROJ-001")

            assert progress["total_milestones"] == 2
            assert progress["completed_milestones"] == 1
            assert progress["progress"] == 50.0


class TestProjectServiceComplete:
    """Test project completion."""

    def test_complete_project_success(self, project_service, temp_dirs, sample_project):
        """Test marking a project as completed."""
        (temp_dirs["projects"] / "project.md").touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=sample_project,
            ),
            patch.object(project_service, "save_project", return_value=True),
        ):
            completed = project_service.complete_project("PROJ-001")

            assert completed is not None
            assert completed.status == ProjectStatus.COMPLETED

    def test_complete_project_not_found(self, project_service):
        """Test completing a non-existent project returns None."""
        result = project_service.complete_project("NONEXISTENT")

        assert result is None

    def test_complete_project_calls_update(
        self, project_service, temp_dirs, sample_project
    ):
        """Test complete_project calls update_project with correct status."""
        (temp_dirs["projects"] / "project.md").touch()

        with (
            patch(
                "roadmap.core.services.project_service.ProjectParser.parse_project_file",
                return_value=sample_project,
            ),
            patch.object(
                project_service, "update_project", return_value=sample_project
            ) as mock_update,
        ):
            project_service.complete_project("PROJ-001")

            mock_update.assert_called_once_with(
                "PROJ-001", status=ProjectStatus.COMPLETED
            )
