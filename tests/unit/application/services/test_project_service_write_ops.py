"""Unit tests for ProjectService - project operations and management."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from roadmap.common.constants import MilestoneStatus
from roadmap.core.domain.project import Project, ProjectStatus
from roadmap.core.services.project.project_service import ProjectService


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
def mock_project_repository():
    """Create a mock ProjectRepository."""
    repo = Mock()
    repo.list.return_value = []
    repo.get.return_value = None
    repo.save.return_value = None
    repo.update.return_value = None
    repo.delete.return_value = True
    return repo


@pytest.fixture
def project_service(mock_project_repository, temp_dirs):
    """Create a ProjectService instance with mock repository."""
    return ProjectService(
        repository=mock_project_repository,
        milestones_dir=temp_dirs["milestones"],
    )


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id="PROJ-001",
        name="Test Project",
        content="A test project",
        status=ProjectStatus.ACTIVE,
        created=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
        updated=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        milestones=["Milestone 1", "Milestone 2"],
    )


class TestProjectServiceSave:
    """Test saving projects."""

    def test_save_project_existing(self, project_service, temp_dirs, sample_project):
        """Test saving an existing project updates the file."""
        project_file = temp_dirs["projects"] / "project.md"
        project_file.touch()

        mock_repository = MagicMock()
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        result = project_service.save_project(sample_project)

        assert result
        mock_repository.save.assert_called_once()
        # Check updated timestamp was set
        assert sample_project.updated is not None

    def test_save_project_new(self, project_service, temp_dirs, sample_project):
        """Test saving a new project creates a file."""
        # No existing files

        mock_repository = MagicMock()
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        result = project_service.save_project(sample_project)

        assert result
        mock_repository.save.assert_called_once()

    def test_save_project_handles_parse_errors(
        self, project_service, temp_dirs, sample_project
    ):
        """Test save_project handles parse errors gracefully."""
        project_file = temp_dirs["projects"] / "project.md"
        project_file.touch()

        # Mock repository that works despite parse errors
        mock_repository = MagicMock()
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        result = project_service.save_project(sample_project)

        assert result
        mock_repository.save.assert_called_once()


class TestProjectServiceCreate:
    """Test project creation."""

    def test_create_project_minimal(self, project_service):
        """Test creating a project with minimal parameters."""
        with patch.object(project_service, "save_project", return_value=True):
            project = project_service.create_project(name="New Project")

            assert project.name == "New Project"
            assert project.headline == ""
            assert project.milestones == []

    def test_create_project_full(self, project_service):
        """Test creating a project with all parameters."""
        with patch.object(project_service, "save_project", return_value=True):
            project = project_service.create_project(
                name="New Project",
                headline="Project description",
                milestones=["M1", "M2"],
            )

            assert project.name == "New Project"
            assert project.headline == "Project description"
            assert project.milestones == ["M1", "M2"]

    def test_create_project_calls_save(self, project_service):
        """Test creating a project calls save_project."""
        with patch.object(
            project_service, "save_project", return_value=True
        ) as mock_save:
            project = project_service.create_project(name="New Project")

            mock_save.assert_called_once_with(project)

    def test_create_project_generates_content(self, project_service):
        """Test created project initializes with empty content."""
        with patch.object(project_service, "save_project", return_value=True):
            project = project_service.create_project(
                name="New Project", headline="Test description"
            )

            # Project starts with empty content
            assert project.content == ""
            assert project.headline == "Test description"


class TestProjectServiceUpdate:
    """Test project updates."""

    def test_update_project_success(self, project_service, temp_dirs, sample_project):
        """Test updating a project successfully."""
        (temp_dirs["projects"] / "project.md").touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        updated = project_service.update_project(
            "PROJ-001", name="Updated Name", headline="Updated Description"
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.headline == "Updated Description"

    def test_update_project_not_found(self, project_service):
        """Test updating a non-existent project returns None."""
        mock_repository = MagicMock()
        mock_repository.get.return_value = None
        project_service.repository = mock_repository

        result = project_service.update_project("NONEXISTENT", name="New Name")

        assert result is None

    def test_update_project_calls_save(
        self, project_service, temp_dirs, sample_project
    ):
        """Test update_project calls save_project."""
        (temp_dirs["projects"] / "project.md").touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        with patch.object(
            project_service, "save_project", return_value=True
        ) as mock_save:
            project_service.update_project("PROJ-001", name="Updated")

            mock_save.assert_called_once()

    def test_update_project_ignores_invalid_fields(
        self, project_service, temp_dirs, sample_project
    ):
        """Test updating with invalid field names is handled."""
        (temp_dirs["projects"] / "project.md").touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        with patch.object(project_service, "save_project", return_value=True):
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

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        mock_repository.delete.return_value = True
        project_service.repository = mock_repository

        result = project_service.delete_project("PROJ-001")

        assert result
        mock_repository.delete.assert_called_once_with("PROJ-001")

    def test_delete_project_not_found(self, project_service):
        """Test deleting a non-existent project returns False."""
        mock_repository = MagicMock()
        mock_repository.get.return_value = None
        project_service.repository = mock_repository

        result = project_service.delete_project("NONEXISTENT")

        assert not result

    def test_delete_project_partial_id(
        self, project_service, temp_dirs, sample_project
    ):
        """Test deleting with partial ID match."""
        project_file = temp_dirs["projects"] / "project.md"
        project_file.touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        mock_repository.delete.return_value = True
        project_service.repository = mock_repository

        result = project_service.delete_project("PROJ")

        assert result
        mock_repository.delete.assert_called_once()

    def test_delete_project_skips_invalid_files(self, project_service, temp_dirs):
        """Test delete_project skips files that can't be parsed."""
        (temp_dirs["projects"] / "invalid.md").touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = None
        project_service.repository = mock_repository

        result = project_service.delete_project("PROJ-001")

        # Should return False, not raise exception
        assert not result


class TestProjectServiceProgress:
    """Test progress calculation."""

    def test_calculate_progress_no_project(self, project_service):
        """Test calculating progress for non-existent project."""
        mock_repository = MagicMock()
        mock_repository.get.return_value = None
        project_service.repository = mock_repository

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

        mock_repository = MagicMock()
        mock_repository.get.return_value = project_without_milestones
        project_service.repository = mock_repository

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

        mock_repository = MagicMock()
        mock_repository.get.return_value = project
        project_service.repository = mock_repository

        # Mock FileEnumerationService.enumerate_and_parse to return our milestones
        with patch(
            "roadmap.core.services.project_service.FileEnumerationService.enumerate_and_parse",
            return_value=[milestone1, milestone2],
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

        mock_repository = MagicMock()
        mock_repository.get.return_value = project
        project_service.repository = mock_repository

        # Mock FileEnumerationService.enumerate_and_parse to return our milestones
        with patch(
            "roadmap.core.services.project_service.FileEnumerationService.enumerate_and_parse",
            return_value=[milestone1, milestone2],
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

        # Setup sample project with ACTIVE status
        sample_project.status = ProjectStatus.ACTIVE

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        completed = project_service.complete_project("PROJ-001")

        assert completed is not None
        assert completed.status == ProjectStatus.COMPLETED

    def test_complete_project_not_found(self, project_service):
        """Test completing a non-existent project returns None."""
        mock_repository = MagicMock()
        mock_repository.get.return_value = None
        project_service.repository = mock_repository

        result = project_service.complete_project("NONEXISTENT")

        assert result is None

    def test_complete_project_calls_update(
        self, project_service, temp_dirs, sample_project
    ):
        """Test complete_project calls update_project with correct status."""
        (temp_dirs["projects"] / "project.md").touch()

        sample_project.status = ProjectStatus.ACTIVE

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        mock_repository.save.return_value = None
        project_service.repository = mock_repository

        with patch.object(
            project_service, "update_project", return_value=sample_project
        ) as mock_update:
            project_service.complete_project("PROJ-001")

            mock_update.assert_called_once_with(
                "PROJ-001", status=ProjectStatus.COMPLETED
            )
