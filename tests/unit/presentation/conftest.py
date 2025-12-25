"""Shared test fixtures and configuration for presentation (CLI) layer tests.

Phase 1B Enhancement (Fixture Optimization):
- Added combo fixtures (runner + mock, runner + core)
- Added initialized_core with proper tmp_path scope
- Added cli_runner_mocked for mock-based tests
- Removes unnecessary isolated_filesystem() nesting
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main
from roadmap.infrastructure.core import RoadmapCore


@pytest.fixture(autouse=True)
def reset_cli_state():
    """Reset CLI state between tests to prevent pollution."""
    # Clear any cached Click contexts and CLI state
    import os
    import sys

    # Store original environment
    original_cwd = os.getcwd()
    original_env = os.environ.copy()

    # Clear Click-related caches if they exist
    if hasattr(main, "make_context"):
        try:
            main.make_context("main", [])
            # Context reset not available, skip
            pass
        except Exception:  # noqa: BLE001
            pass

    # Clear any module-level state
    if hasattr(sys.modules.get("roadmap.cli"), "_cached_core"):
        delattr(sys.modules["roadmap.cli"], "_cached_core")

    yield

    # Restore original state
    os.chdir(original_cwd)
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def cli_runner():
    """Create an isolated CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_cwd)


@pytest.fixture
def cli_isolated_fs():
    """CLI runner with isolated filesystem."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        yield runner


@pytest.fixture
def initialized_roadmap():
    """Provide a CliRunner with an initialized roadmap in isolated filesystem."""
    from roadmap.infrastructure.core import RoadmapCore

    runner = CliRunner()

    with runner.isolated_filesystem():
        # Initialize the roadmap
        manager = RoadmapCore()
        manager.initialize()

        yield runner


@pytest.fixture
def mock_github_client():
    """Mock GitHub client for testing sync operations."""
    with patch("roadmap.adapters.github.github.GitHubClient") as mock:
        # Mock successful authentication
        mock.return_value.test_connection.return_value = True
        mock.return_value.get_issues.return_value = []
        mock.return_value.get_milestones.return_value = []
        mock.return_value.create_issue.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/test/issues/1",
        }
        mock.return_value.create_milestone.return_value = {
            "number": 1,
            "html_url": "https://github.com/test/test/milestones/1",
        }
        yield mock


# ============================================================================
# Phase 1B: Combo Fixtures (Fixture Optimization)
# ============================================================================


@pytest.fixture
def cli_runner_mocked():
    """CLI runner + mock core combo fixture.

    Use this for tests that mock the RoadmapCore (don't need real filesystem).
    Returns: (CliRunner, MagicMock core)

    Example:
        def test_something(cli_runner_mocked):
            runner, mock_core = cli_runner_mocked
            mock_core.team.validate_assignee.return_value = (True, "")
            result = runner.invoke(command, obj=mock_core)
            assert result.exit_code == 0
    """
    from click.testing import CliRunner

    runner = CliRunner()
    mock_core = MagicMock()
    return runner, mock_core


@pytest.fixture
def initialized_core(tmp_path):
    """Initialized RoadmapCore instance with real filesystem.

    Use this for tests that need a real database but don't need CliRunner.
    Returns: RoadmapCore instance initialized in tmp_path

    Example:
        def test_something(initialized_core):
            core = initialized_core
            core.create_issue("Test")
            issues = core.list_issues()
            assert len(issues) == 1
    """
    core = RoadmapCore(root_path=tmp_path)
    core.initialize()
    return core


@pytest.fixture
def cli_runner_initialized():
    """CLI runner with pre-initialized roadmap in isolated filesystem.

    Use this for integration tests that need both CliRunner and a real database
    initialized within the CliRunner's isolated filesystem context.
    Returns: (CliRunner, RoadmapCore instance)

    The roadmap is initialized within the runner's isolated filesystem,
    ensuring file operations are contained.

    Example:
        def test_something(cli_runner_initialized):
            runner, core = cli_runner_initialized
            result = runner.invoke(command, obj=core)
            assert result.exit_code == 0
            issues = core.list_issues()
            assert len(issues) > 0
    """
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Initialize roadmap within the isolated filesystem
        core = RoadmapCore()
        core.initialize()
        yield runner, core


# ============================================================================
# Phase 1C: Service-Specific Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_github_service():
    """Mock GitHub service with realistic behavior.

    Use this for tests that need to mock GitHub API interactions.
    Returns: MagicMock configured as GitHubService

    Example:
        def test_something(mock_github_service):
            mock_github_service.get_issues.return_value = [...]
            service = GitHubService(mock=mock_github_service)
            issues = service.get_issues()
            assert len(issues) > 0
    """
    mock_service = MagicMock()
    mock_service.test_connection.return_value = True
    mock_service.get_issues.return_value = []
    mock_service.get_milestones.return_value = []
    mock_service.create_issue.return_value = {
        "number": 1,
        "html_url": "https://github.com/test/repo/issues/1",
    }
    mock_service.update_issue.return_value = True
    mock_service.delete_issue.return_value = True
    mock_service.validate_assignee.return_value = (True, "")
    mock_service.get_team_members.return_value = []
    return mock_service


@pytest.fixture
def mock_git_service():
    """Mock Git service with realistic behavior.

    Use this for tests that need to mock Git operations.
    Returns: MagicMock configured as GitService

    Example:
        def test_something(mock_git_service):
            mock_git_service.is_repository.return_value = True
            service = GitService(mock=mock_git_service)
            assert service.is_repository()
    """
    mock_service = MagicMock()
    mock_service.is_repository.return_value = True
    mock_service.get_current_branch.return_value = "main"
    mock_service.get_commits.return_value = []
    mock_service.create_branch.return_value = True
    mock_service.delete_branch.return_value = True
    mock_service.install_hooks.return_value = True
    return mock_service


@pytest.fixture
def mock_comments_handler():
    """Mock Comments handler with realistic behavior.

    Use this for tests that need to mock comment operations.
    Returns: MagicMock configured as CommentsHandler

    Example:
        def test_something(mock_comments_handler):
            mock_comments_handler.get_comments.return_value = [...]
            handler = CommentsHandler(mock=mock_comments_handler)
            comments = handler.get_comments("issue-1")
            assert len(comments) >= 0
    """
    mock_handler = MagicMock()
    mock_handler.get_issue_comments.return_value = []
    mock_handler.create_comment.return_value = {"id": 123456}
    mock_handler.update_comment.return_value = True
    mock_handler.delete_comment.return_value = True
    return mock_handler
