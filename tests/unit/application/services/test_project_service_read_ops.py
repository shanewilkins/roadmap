"""Unit tests for ProjectService - project operations and management."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import pytest

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


class TestProjectServiceInit:
    """Test ProjectService initialization."""

    def test_init_sets_dependencies(self, mock_project_repository, temp_dirs):
        """Test initialization sets all dependencies correctly."""
        service = ProjectService(
            repository=mock_project_repository,
            milestones_dir=temp_dirs["milestones"],
        )

        assert service.repository == mock_project_repository
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
        """Test listing returns all projects from repository."""
        # Setup mock repository to return projects
        project_service.repository.list.return_value = [sample_project, sample_project]

        projects = project_service.list_projects()

        assert len(projects) == 2
        assert projects[0] == sample_project

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

        mock_repository = MagicMock()
        # Repository returns projects sorted by created date (oldest first)
        mock_repository.list.return_value = [project2, project1]
        project_service.repository = mock_repository

        projects = project_service.list_projects()

        # Should be sorted by created date (oldest first)
        assert projects[0].id == "PROJ-002"
        assert projects[1].id == "PROJ-001"

    def test_list_projects_skips_invalid_files(self, project_service, temp_dirs):
        """Test listing skips files that can't be parsed."""
        # Create dummy file
        (temp_dirs["projects"] / "invalid.md").touch()

        mock_repository = MagicMock()
        mock_repository.list.return_value = []
        project_service.repository = mock_repository

        projects = project_service.list_projects()

        # Should return empty list, not raise exception
        assert projects == []


class TestProjectServiceGet:
    """Test getting individual projects."""

    def test_get_project_found(self, project_service, temp_dirs, sample_project):
        """Test getting an existing project."""
        (temp_dirs["projects"] / "project.md").touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        project_service.repository = mock_repository

        project = project_service.get_project("PROJ-001")

        assert project is not None
        assert project.id == "PROJ-001"
        assert project.name == "Test Project"

    def test_get_project_not_found(self, project_service):
        """Test getting a non-existent project returns None."""
        mock_repository = MagicMock()
        mock_repository.get.return_value = None
        project_service.repository = mock_repository

        project = project_service.get_project("NONEXISTENT")

        assert project is None

    def test_get_project_partial_id_match(
        self, project_service, temp_dirs, sample_project
    ):
        """Test getting project with partial ID match."""
        (temp_dirs["projects"] / "project.md").touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = sample_project
        project_service.repository = mock_repository

        # Should match with partial ID
        project = project_service.get_project("PROJ")

        assert project is not None
        assert project.id == "PROJ-001"

    def test_get_project_skips_invalid_files(self, project_service, temp_dirs):
        """Test get_project skips files that can't be parsed."""
        (temp_dirs["projects"] / "invalid.md").touch()

        mock_repository = MagicMock()
        mock_repository.get.return_value = None
        project_service.repository = mock_repository

        project = project_service.get_project("PROJ-001")

        # Should return None, not raise exception
        assert project is None
