"""Performance-optimized fixtures for fast test execution.

Provides fixtures that are optimized for speed, including session-scoped
resources, selective mocking, and filesystem optimizations.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest


@pytest.fixture(scope="session")
def performance_test_config():
    """Configuration for performance-optimized tests.

    Returns:
        Dict with performance optimization settings
    """
    return {
        "enable_mocking": True,
        "skip_filesystem": True,
        "mock_git_operations": True,
        "lightweight_fixtures": True,
    }


@pytest.fixture(scope="session")
def shared_git_repo(tmp_path_factory):
    """Session-scoped git repository for reuse across slow tests.

    Major performance optimization: creates git repo once per session,
    copies for tests that need isolation.

    Returns:
        Path to shared git repository
    """
    repo_path = tmp_path_factory.mktemp("shared_git_repo")

    # Initialize git repository once
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
    )

    # Create initial commit
    readme = repo_path / "README.md"
    readme.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

    return repo_path


@pytest.fixture
def optimized_git_repo(shared_git_repo, tmp_path):
    """Fast git repository by copying from shared session fixture.

    Performance optimization: Copy existing git repo instead of
    initializing from scratch every time.

    Returns:
        Path to copied git repository
    """
    import shutil

    repo_copy = tmp_path / "git_repo_copy"
    shutil.copytree(shared_git_repo, repo_copy)
    return repo_copy


@pytest.fixture
def patch_filesystem_operations():
    """Patch heavy filesystem operations for faster tests.

    Mocks mkdir and write_text operations to avoid actual disk I/O
    for tests that don't need real filesystem operations.

    Returns:
        Dict with mocked operations
    """
    with (
        patch("roadmap.core.RoadmapCore.initialize") as mock_init,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.write_text") as mock_write,
    ):
        mock_init.return_value = True
        mock_mkdir.return_value = None
        mock_write.return_value = None

        yield {"init": mock_init, "mkdir": mock_mkdir, "write_text": mock_write}


@pytest.fixture
def mock_git_operations():
    """Mock non-essential git operations for performance.

    Selectively mocks git operations that don't affect core testing.
    Major performance optimization for integration tests.

    Note: repository_scanner has been moved to future/ (post-1.0 feature).
    This fixture is kept for backward compatibility but returns a simple mock.

    Returns:
        Dict with mocked git operations
    """
    yield {"scan_commit_history": Mock(), "scan_branch_history": Mock()}


@pytest.fixture
def selective_git_mock():
    """Selectively mock only expensive git operations.

    Keeps essential git operations real for integration testing,
    mocks only the performance bottlenecks.

    Mocks: log, stat, oneline, rev-list, ls-files
    Real: Other git operations
    """

    def mock_selective_run(*args, **kwargs):
        """Mock function that selectively handles git commands."""
        import subprocess as real_subprocess

        if args and isinstance(args[0], list):
            cmd = args[0]
            # Mock expensive operations
            if "git" in cmd and any(
                expensive in cmd
                for expensive in ["log", "--stat", "--oneline", "rev-list", "ls-files"]
            ):
                result = Mock()
                result.returncode = 0
                result.stdout = "mocked output"
                result.stderr = ""
                return result

        # Use real subprocess for essential operations
        return real_subprocess.run(*args, **kwargs)

    with patch("subprocess.run", side_effect=mock_selective_run):
        yield


@pytest.fixture(scope="session")
def session_mock_github_client():
    """Session-scoped GitHub client mock for performance.

    Returns:
        Mock GitHub client with basic methods
    """
    mock_client = Mock()
    mock_client.is_authenticated = True
    mock_client.owner = "test-owner"
    mock_client.repo = "test-repo"
    mock_client.get_issues.return_value = []
    mock_client.get_milestones.return_value = []
    return mock_client
