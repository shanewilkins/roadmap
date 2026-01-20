"""Mock fixtures for core objects and data.

Provides standardized mock objects for RoadmapCore, configuration, issues,
milestones, and other core domain objects.

This module centralizes all mock fixtures to avoid duplication across test files.
Tests should import these fixtures from here rather than defining their own.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from tests.unit.domain.test_data_factory_generation import TestDataFactory


@pytest.fixture(scope="function")
def mock_core():
    """Create standardized mock RoadmapCore instance.

    This centralizes the mock_core fixture used across multiple test files.
    Individual tests can override specific behavior as needed.

    Returns:
        Mock RoadmapCore instance
    """
    return TestDataFactory.create_mock_core()


@pytest.fixture(scope="function")
def mock_core_initialized():
    """Create initialized mock RoadmapCore instance.

    Use this when you need a core that is already initialized.

    Returns:
        Initialized Mock RoadmapCore instance
    """
    return TestDataFactory.create_mock_core(is_initialized=True)


@pytest.fixture(scope="function")
def mock_core_with_github():
    """Create mock RoadmapCore with GitHub integration.

    Use this when testing GitHub-related operations.

    Returns:
        Mock RoadmapCore with GitHub service
    """
    return TestDataFactory.create_mock_core(
        is_initialized=True, github_service=MagicMock()
    )


@pytest.fixture(scope="function")
def mock_core_simple():
    """Create simple MagicMock core for basic tests.

    Use this when TestDataFactory.create_mock_core() is overkill.
    Useful for CLI tests that just need a mock object.

    Returns:
        Simple MagicMock instance
    """
    return MagicMock()


@pytest.fixture(scope="function")
def mock_config():
    """Create standardized mock RoadmapConfig instance.

    Returns:
        Mock RoadmapConfig instance
    """
    return TestDataFactory.create_mock_config()


@pytest.fixture(scope="function")
def mock_issue():
    """Create standardized mock Issue instance.

    Returns:
        Mock Issue instance
    """
    return TestDataFactory.create_mock_issue()


@pytest.fixture(scope="function")
def mock_milestone():
    """Create standardized mock Milestone instance.

    Returns:
        Mock Milestone instance
    """
    return TestDataFactory.create_mock_milestone()


@pytest.fixture
def lightweight_mock_core():
    """Create lightweight mock core for performance-critical tests.

    This provides minimal mocking for tests that don't need full core functionality.
    Suitable for unit tests that only need basic initialization check.

    Returns:
        Lightweight Mock RoadmapCore instance
    """
    core = Mock()
    core.is_initialized.return_value = True
    core.get_issues.return_value = []
    return core


@pytest.fixture
def fast_mock_core():
    """Create ultra-lightweight mock core with minimal setup.

    Even faster than lightweight_mock_core, useful for performance-critical paths.

    Returns:
        Ultra-lightweight Mock RoadmapCore instance
    """
    core = Mock()
    core.is_initialized.return_value = True
    core.workspace_root = Path("/tmp/fast_test")
    core.get_issues.return_value = []
    core.get_milestones.return_value = []
    return core


@pytest.fixture
def cli_test_data():
    """Create CLI test data factory function.

    Returns:
        TestDataFactory class for creating test data
    """
    return TestDataFactory


@pytest.fixture
def mock_console():
    """Create mock Rich console for output testing.

    Use this when testing commands that use Rich for output.
    Allows verification of console calls without actual output.

    Returns:
        Mock console instance
    """
    return MagicMock()


@pytest.fixture
def mock_persistence():
    """Create mock PersistenceInterface for testing.

    Use this when testing services that depend on persistence without
    touching actual filesystem or database.

    Returns:
        MagicMock with PersistenceInterface spec
    """
    from roadmap.core.interfaces.persistence import PersistenceInterface

    return MagicMock(spec=PersistenceInterface)


@pytest.fixture
def roadmap_core():
    """Create actual RoadmapCore instance for integration-style tests.

    Use this when you need a real RoadmapCore instance initialized with
    actual services but in an isolated workspace.

    Returns:
        RoadmapCore instance in a temporary workspace
    """
    import tempfile
    from pathlib import Path

    from roadmap.infrastructure.coordination.core import RoadmapCore

    # Create temporary workspace for this test
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up minimal roadmap structure
        roadmap_dir = Path(tmpdir) / ".roadmap"
        roadmap_dir.mkdir()
        (roadmap_dir / "issues").mkdir()
        (roadmap_dir / "milestones").mkdir()

        # Create core instance
        core = RoadmapCore()
        yield core


@pytest.fixture
def mock_git_service():
    """Create mock GitService for testing.

    Returns:
        MagicMock with GitService spec
    """
    from roadmap.core.services.git.git_service import GitService

    return MagicMock(spec=GitService)


@pytest.fixture
def mock_github_client():
    """Create mock GitHub client for testing.

    Returns:
        MagicMock with GitHubBackendInterface spec
    """
    from roadmap.core.interfaces.sync import GitHubBackendInterface

    return MagicMock(spec=GitHubBackendInterface)


# ============================================================================
# Repository Fixtures
# ============================================================================


@pytest.fixture
def mock_repo():
    """Create standardized mock Repository instance.

    Returns:
        Mock repository with common methods
    """
    mock_repo = Mock()
    mock_repo.list = Mock(return_value=[])
    mock_repo.get = Mock(return_value=None)
    mock_repo.save = Mock(return_value=None)
    mock_repo.link_issue = Mock(return_value=None)
    mock_repo.get_remote_id = Mock(return_value=None)
    mock_repo.get_issue_uuid = Mock(return_value=None)
    return mock_repo


# ============================================================================
# Service Fixtures
# ============================================================================


@pytest.fixture
def mock_sync_service():
    """Create mock Sync service for testing.

    Returns:
        Configured Mock Sync service
    """
    mock_sync = Mock()
    mock_sync.pull = Mock(return_value={"issues": [], "conflicts": []})
    mock_sync.push = Mock(return_value={"success": True})
    return mock_sync


# ============================================================================
# File/Filesystem Fixtures
# ============================================================================


@pytest.fixture
def mock_path():
    """Create mock Path object for filesystem operations.

    Returns:
        Configured Mock Path object
    """
    from pathlib import Path

    mock_path_obj = Mock(spec=Path)
    mock_path_obj.exists = Mock(return_value=True)
    mock_path_obj.is_dir = Mock(return_value=False)
    mock_path_obj.is_file = Mock(return_value=True)
    mock_path_obj.name = "test.txt"
    mock_path_obj.read_text = Mock(return_value="")
    mock_path_obj.write_text = Mock(return_value=None)
    mock_path_obj.relative_to = Mock(return_value=Path("test.txt"))
    mock_path_obj.glob = Mock(return_value=[])
    mock_path_obj.iterdir = Mock(return_value=[])
    return mock_path_obj


@pytest.fixture
def mock_file_handle():
    """Create mock file handle for file operations.

    Returns:
        Configured Mock file handle
    """
    mock_file = Mock()
    mock_file.read = Mock(return_value="")
    mock_file.write = Mock(return_value=0)
    mock_file.__enter__ = Mock(return_value=mock_file)
    mock_file.__exit__ = Mock(return_value=None)
    return mock_file


@pytest.fixture
def mock_directory():
    """Create mock directory/path object.

    Returns:
        Configured Mock directory
    """
    mock_dir = Mock()
    mock_dir.exists = Mock(return_value=True)
    mock_dir.is_dir = Mock(return_value=True)
    mock_dir.iterdir = Mock(return_value=[])
    mock_dir.glob = Mock(return_value=[])
    return mock_dir


# ============================================================================
# Domain Entity Fixtures
# ============================================================================


@pytest.fixture
def mock_issue_entity():
    """Create standardized mock Issue entity.

    Returns:
        Mock Issue instance
    """
    from roadmap.core.domain.issue import Issue

    mock_issue_obj = Mock(spec=Issue)
    mock_issue_obj.id = "issue-1"
    mock_issue_obj.title = "Test Issue"
    mock_issue_obj.status = "TODO"
    mock_issue_obj.priority = "MEDIUM"
    return mock_issue_obj


@pytest.fixture
def mock_milestone_entity():
    """Create standardized mock Milestone entity.

    Returns:
        Mock Milestone instance
    """
    from roadmap.core.domain.milestone import Milestone

    mock_milestone_obj = Mock(spec=Milestone)
    mock_milestone_obj.id = "milestone-1"
    mock_milestone_obj.name = "v1.0"
    mock_milestone_obj.status = "IN_PROGRESS"
    return mock_milestone_obj


@pytest.fixture
def mock_comment_entity():
    """Create standardized mock Comment entity.

    Returns:
        Mock Comment instance
    """
    from roadmap.core.domain.comment import Comment

    mock_comment_obj = Mock(spec=Comment)
    mock_comment_obj.id = "comment-1"
    mock_comment_obj.author = "test_user"
    mock_comment_obj.content = "Test comment"
    return mock_comment_obj


@pytest.fixture
def mock_project_entity():
    """Create standardized mock Project entity.

    Returns:
        Mock Project instance
    """
    from roadmap.core.domain.project import Project

    mock_project_obj = Mock(spec=Project)
    mock_project_obj.id = "project-1"
    mock_project_obj.name = "Test Project"
    return mock_project_obj


# ============================================================================
# Interface Fixtures
# ============================================================================


@pytest.fixture
def mock_persistence_interface():
    """Create mock PersistenceInterface for testing.

    Returns:
        MagicMock with PersistenceInterface spec
    """
    from roadmap.core.interfaces.persistence import PersistenceInterface

    return MagicMock(spec=PersistenceInterface)


@pytest.fixture
def mock_issue_parser_interface():
    """Create mock IssueParserInterface for testing.

    Returns:
        MagicMock with IssueParserInterface spec
    """
    from roadmap.core.interfaces.parsers import IssueParserInterface

    return MagicMock(spec=IssueParserInterface)


# ============================================================================
# UI/Presentation Fixtures
# ============================================================================


@pytest.fixture
def mock_table_data():
    """Create mock TableData for presentation testing.

    Returns:
        Configured Mock TableData
    """
    from rich.table import Table

    mock_table = Mock(spec=Table)
    mock_table.rows = []
    mock_table.columns = []
    return mock_table


# ============================================================================
# Fixture Factories - Create multiple variants for different scenarios
# ============================================================================


@pytest.fixture
def mock_roadmap_core_factory(tmp_path):
    """Factory fixture that creates mock RoadmapCore instances with custom roadmap_dir.

    This allows tests to get a fresh mock core with the roadmap_dir already configured,
    eliminating the need for builder functions when the only customization needed is
    the roadmap directory path.

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Function that creates mock RoadmapCore with roadmap_dir set

    Usage:
        def test_something(mock_roadmap_core_factory):
            mock_core = mock_roadmap_core_factory()  # Uses default tmp_path
            # OR
            mock_core = mock_roadmap_core_factory(roadmap_dir=custom_path)
    """
    from roadmap.infrastructure.coordination.core import RoadmapCore

    def _factory(roadmap_dir=None, has_github=False, has_repository=True):
        if roadmap_dir is None:
            roadmap_dir = tmp_path / ".roadmap"

        mock_core = Mock(spec=RoadmapCore)
        mock_core.roadmap_dir = roadmap_dir

        if has_repository:
            mock_core.issue_service = Mock()
            mock_core.issue_service.repository = Mock()
            mock_core.issue_service.repository.list = Mock(return_value=[])
            mock_core.issue_service.repository.get = Mock(return_value=None)
            mock_core.issue_service.repository.save = Mock(return_value=None)

        if has_github:
            mock_core.github_service = Mock()

        return mock_core

    return _factory


@pytest.fixture
def mock_core_with_repo_factory():
    """Factory fixture that creates mock RoadmapCore with custom repository behavior.

    Replaces build_mock_core_with_repo() calls in test methods.

    Returns:
        Function that creates mock RoadmapCore with customized repository

    Usage:
        def test_something(mock_core_with_repo_factory):
            mock_core = mock_core_with_repo_factory(list_return=[issue1, issue2])
            # OR
            mock_core = mock_core_with_repo_factory(save_side_effect=Exception("Save failed"))
    """
    from roadmap.infrastructure.coordination.core import RoadmapCore

    def _factory(
        list_return=None,
        get_return=None,
        save_side_effect=None,
        link_issue_return=None,
        link_issue_side_effect=None,
        get_remote_id_return=None,
        get_issue_uuid_return=None,
    ):
        mock_core = Mock(spec=RoadmapCore)
        mock_core.issue_service = Mock()

        # Create repository with customized behavior
        mock_repo = Mock()

        if list_return is not None:
            mock_repo.list = Mock(return_value=list_return)
        else:
            mock_repo.list = Mock(return_value=[])

        if get_return is not None:
            mock_repo.get = Mock(return_value=get_return)
        else:
            mock_repo.get = Mock(return_value=None)

        if save_side_effect is not None:
            mock_repo.save = Mock(side_effect=save_side_effect)
        else:
            mock_repo.save = Mock(return_value=None)

        if link_issue_side_effect is not None:
            mock_repo.link_issue = Mock(side_effect=link_issue_side_effect)
        elif link_issue_return is not None:
            mock_repo.link_issue = Mock(return_value=link_issue_return)
        else:
            mock_repo.link_issue = Mock(return_value=None)

        if get_remote_id_return is not None:
            mock_repo.get_remote_id = Mock(return_value=get_remote_id_return)
        else:
            mock_repo.get_remote_id = Mock(return_value=None)

        if get_issue_uuid_return is not None:
            mock_repo.get_issue_uuid = Mock(return_value=get_issue_uuid_return)
        else:
            mock_repo.get_issue_uuid = Mock(return_value=None)

        mock_core.issue_service.repository = mock_repo
        return mock_core

    return _factory


@pytest.fixture
def mock_core_with_projects(tmp_path):
    """Fixture that provides a mock RoadmapCore with projects directory already created.

    Eliminates boilerplate setup code in tests that need a projects directory.

    Returns:
        Mock RoadmapCore with projects directory ready to use
    """
    from roadmap.infrastructure.coordination.core import RoadmapCore

    mock_core = Mock(spec=RoadmapCore)
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir(exist_ok=True)
    (roadmap_dir / "projects").mkdir(exist_ok=True)
    mock_core.roadmap_dir = roadmap_dir

    return mock_core


@pytest.fixture
def mock_issue_factory():
    """Factory fixture that creates mock Issue entities with custom attributes.

    Replaces build_mock_issue() calls in test methods.

    Returns:
        Function that creates configured Mock Issue instances
    """
    from roadmap.core.domain.issue import Issue

    def _factory(
        id="issue-1", title="Test Issue", status="TODO", priority="MEDIUM", **kwargs
    ):
        mock_issue = Mock(spec=Issue)
        mock_issue.id = id
        mock_issue.title = title
        mock_issue.status = status
        mock_issue.priority = priority
        for key, value in kwargs.items():
            setattr(mock_issue, key, value)
        return mock_issue

    return _factory


@pytest.fixture
def mock_milestone_factory():
    """Factory fixture that creates mock Milestone entities with custom attributes.

    Replaces build_mock_milestone() calls in test methods.

    Returns:
        Function that creates configured Mock Milestone instances
    """
    from roadmap.core.domain.milestone import Milestone

    def _factory(id="milestone-1", name="v1.0", status="IN_PROGRESS", **kwargs):
        mock_milestone = Mock(spec=Milestone)
        mock_milestone.id = id
        mock_milestone.name = name
        mock_milestone.status = status
        for key, value in kwargs.items():
            setattr(mock_milestone, key, value)
        return mock_milestone

    return _factory


@pytest.fixture
def mock_comment_factory():
    """Factory fixture that creates mock Comment entities with custom attributes.

    Replaces build_mock_comment() calls in test methods.

    Returns:
        Function that creates configured Mock Comment instances
    """
    from roadmap.core.domain.comment import Comment

    def _factory(id="comment-1", author="test_user", content="Test comment", **kwargs):
        mock_comment = Mock(spec=Comment)
        mock_comment.id = id
        mock_comment.author = author
        mock_comment.content = content
        for key, value in kwargs.items():
            setattr(mock_comment, key, value)
        return mock_comment

    return _factory


@pytest.fixture
def mock_project_factory():
    """Factory fixture that creates mock Project entities with custom attributes.

    Replaces build_mock_project() calls in test methods.

    Returns:
        Function that creates configured Mock Project instances
    """
    from roadmap.core.domain.project import Project

    def _factory(id="project-1", name="Test Project", **kwargs):
        mock_project = Mock(spec=Project)
        mock_project.id = id
        mock_project.name = name
        for key, value in kwargs.items():
            setattr(mock_project, key, value)
        return mock_project

    return _factory


@pytest.fixture
def mock_repo_factory():
    """Factory fixture that creates mock Repository with custom behavior.

    Replaces build_mock_repo() calls in test methods.

    Returns:
        Function that creates configured Mock Repository instances
    """

    def _factory(
        list_return=None,
        get_return=None,
        save_side_effect=None,
        link_issue_return=None,
        link_issue_side_effect=None,
        get_remote_id_return=None,
        get_issue_uuid_return=None,
    ):
        mock_repo = Mock()

        if list_return is not None:
            mock_repo.list = Mock(return_value=list_return)
        else:
            mock_repo.list = Mock(return_value=[])

        if get_return is not None:
            mock_repo.get = Mock(return_value=get_return)
        else:
            mock_repo.get = Mock(return_value=None)

        if save_side_effect is not None:
            mock_repo.save = Mock(side_effect=save_side_effect)
        else:
            mock_repo.save = Mock(return_value=None)

        if link_issue_side_effect is not None:
            mock_repo.link_issue = Mock(side_effect=link_issue_side_effect)
        elif link_issue_return is not None:
            mock_repo.link_issue = Mock(return_value=link_issue_return)
        else:
            mock_repo.link_issue = Mock(return_value=None)

        if get_remote_id_return is not None:
            mock_repo.get_remote_id = Mock(return_value=get_remote_id_return)
        else:
            mock_repo.get_remote_id = Mock(return_value=None)

        if get_issue_uuid_return is not None:
            mock_repo.get_issue_uuid = Mock(return_value=get_issue_uuid_return)
        else:
            mock_repo.get_issue_uuid = Mock(return_value=None)

        return mock_repo

    return _factory


# ============================================================================
# Path/Filesystem Fixture Factories
# ============================================================================


@pytest.fixture
def mock_path_factory():
    """Factory fixture that creates mock Path objects with custom filesystem state.

    Replaces build_mock_path() calls in test methods.

    Returns:
        Function that creates configured Mock Path instances
    """

    def _factory(
        name="test.txt",
        exists=True,
        is_dir=False,
        is_file=True,
        content="",
        glob_results=None,
    ):
        from pathlib import Path

        mock_path = Mock(spec=Path)
        mock_path.exists = Mock(return_value=exists)
        mock_path.is_dir = Mock(return_value=is_dir)
        mock_path.is_file = Mock(return_value=is_file)
        mock_path.name = name
        mock_path.read_text = Mock(return_value=content)
        mock_path.write_text = Mock(return_value=None)
        mock_path.relative_to = Mock(return_value=Path(name))

        if glob_results is None:
            glob_results = []
        mock_path.glob = Mock(return_value=glob_results)
        mock_path.iterdir = Mock(return_value=glob_results)

        return mock_path

    return _factory
