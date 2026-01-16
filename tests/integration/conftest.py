"""Integration test fixtures and configuration.

Provides fixtures specific to integration testing, including
real filesystem operations, git repository setup, and complete
environment setup for testing multiple components together.
"""

import os
import subprocess
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def integration_runner():
    """Create a CLI runner for integration tests.

    Returns:
        Click CliRunner instance
    """
    return CliRunner()


@pytest.fixture
def real_git_repo(tmp_path):
    """Create a real git repository for integration testing.

    Provides a fully initialized git repository with initial commit
    for testing git integration features.

    Returns:
        Path to git repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repository
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
def initialized_roadmap_repo(real_git_repo):
    """Create a git repo with initialized roadmap structure.

    Combines a real git repository with an initialized roadmap
    for testing complete workflows.

    Returns:
        Path to initialized roadmap repository
    """
    from roadmap.infrastructure.coordination.core import RoadmapCore

    original_cwd = os.getcwd()
    os.chdir(real_git_repo)

    try:
        # Initialize roadmap
        core = RoadmapCore()
        core.initialize()
        yield real_git_repo
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def multi_branch_git_repo(real_git_repo):
    """Create a git repo with multiple branches.

    Useful for testing branch-aware features.

    Returns:
        Path to git repository with branches
    """
    # Create and switch to a new branch
    subprocess.run(
        ["git", "checkout", "-b", "feature/test"],
        cwd=real_git_repo,
        check=True,
        capture_output=True,
    )

    # Create a commit on the branch
    feature_file = real_git_repo / "feature.md"
    feature_file.write_text("# Feature\n")
    subprocess.run(["git", "add", "feature.md"], cwd=real_git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add feature"],
        cwd=real_git_repo,
        check=True,
        capture_output=True,
    )

    # Switch back to main
    subprocess.run(
        ["git", "checkout", "master"],
        cwd=real_git_repo,
        check=True,
        capture_output=True,
    )

    return real_git_repo


@pytest.fixture
def mock_github_api():
    """Mock GitHub API for integration testing.

    Provides mocked GitHub API responses without making real API calls.

    Returns:
        Mock GitHub API client
    """
    with patch("roadmap.sync.GitHubClient") as mock_client_class:
        mock_client = Mock()
        mock_client.is_authenticated = True
        mock_client.owner = "test-owner"
        mock_client.repo = "test-repo"
        mock_client.get_issues.return_value = []
        mock_client.get_milestones.return_value = []
        mock_client.create_issue.return_value = {"id": 1, "number": 1}
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def integration_environment(tmp_path):
    """Create a complete integration test environment.

    Sets up:
    - Temporary working directory
    - Git repository
    - Initialized roadmap
    - Isolated environment variables

    Returns:
        Tuple of (workspace_path, git_repo_path, runner)
    """
    original_cwd = os.getcwd()
    original_env = os.environ.copy()

    workspace = tmp_path / "integration_env"
    workspace.mkdir()

    try:
        os.chdir(workspace)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=workspace,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=workspace,
            check=True,
        )

        # Create initial commit
        readme = workspace / "README.md"
        readme.write_text("# Test Project\n")
        subprocess.run(["git", "add", "README.md"], cwd=workspace, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        # Initialize roadmap
        from roadmap.infrastructure.coordination.core import RoadmapCore

        core = RoadmapCore()
        core.initialize()

        runner = CliRunner()

        yield workspace, core, runner

    finally:
        os.chdir(original_cwd)
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def cli_with_initialized_roadmap(temp_workspace):
    """Create a CLI runner in an initialized roadmap workspace.

    Returns:
        Tuple of (runner, workspace_path)
    """
    from roadmap.infrastructure.coordination.core import RoadmapCore

    original_cwd = os.getcwd()
    os.chdir(temp_workspace)

    try:
        core = RoadmapCore()
        core.initialize()
        runner = CliRunner()
        yield runner, temp_workspace
    finally:
        os.chdir(original_cwd)
