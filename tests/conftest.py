"""Global test configuration and fixtures."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.shared.logging import configure_for_testing

from .unit.domain.test_data_factory import TestDataFactory
from .unit.shared.test_utils import (
    assert_in_output,
    assert_output_contains,
    clean_cli_output,
    strip_ansi,
)


@pytest.fixture(autouse=True, scope="session")
def setup_test_logging():
    """Configure logging for all tests to prevent production logging from breaking tests."""
    configure_for_testing()


@pytest.fixture
def strip_ansi_fixture():
    """Provide ANSI stripping utility to tests."""
    return strip_ansi


@pytest.fixture
def clean_output():
    """Provide CLI output cleaning utility to tests."""
    return clean_cli_output


@pytest.fixture
def assert_output():
    """Provide output assertion helpers to tests."""
    return {
        "assert_in": assert_in_output,
        "assert_contains": assert_output_contains,
        "clean": clean_cli_output,
        "strip": strip_ansi,
    }


@pytest.fixture(autouse=True, scope="function")
def isolate_roadmap_workspace(request, tmp_path):
    """Isolate each test in a temporary directory unless it's marked as unit test

    PERFORMANCE OPTIMIZATION: Skip isolation for unit tests that don't need filesystem operations.
    """
    # Skip isolation for unit tests - major performance win
    if hasattr(request.node, "get_closest_marker"):
        if request.node.get_closest_marker("unit"):
            yield
            return

    # Store original state - ensure we have a valid working directory first
    try:
        original_cwd = os.getcwd()
    except (FileNotFoundError, OSError):
        # If current directory doesn't exist, use tmp_path as fallback
        original_cwd = str(tmp_path)
        os.chdir(original_cwd)

    original_env = os.environ.copy()

    try:
        # Clean up any existing .roadmap artifacts in current directory
        current_roadmap = Path.cwd() / ".roadmap"
        if current_roadmap.exists() and current_roadmap.is_dir():
            # Only clean if it looks like a test artifact (not a real project)
            config_file = current_roadmap / "config.yaml"
            if config_file.exists() and "Test Project" in config_file.read_text():
                import shutil

                shutil.rmtree(current_roadmap, ignore_errors=True)

        # Yield control to the test
        yield

    finally:
        # Always restore original working directory and environment
        try:
            if os.path.exists(original_cwd):
                os.chdir(original_cwd)
            else:
                # Original directory no longer exists, use a safe fallback
                os.chdir(str(tmp_path))
        except (FileNotFoundError, OSError):
            # If all else fails, ensure we're in a valid directory
            os.chdir(str(tmp_path))

        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def roadmap_workspace():
    """Provide a clean roadmap workspace for tests that need it explicitly.

    This is a non-autouse version of the isolation fixture for tests
    that want to explicitly control their workspace setup.
    """
    # Store original state
    original_cwd = os.getcwd()

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create .roadmap directory structure
        roadmap_dir = temp_path / ".roadmap"
        roadmap_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (roadmap_dir / "issues").mkdir(exist_ok=True)
        (roadmap_dir / "milestones").mkdir(exist_ok=True)

        # Create basic config
        config_file = roadmap_dir / "config.yaml"
        config_file.write_text("""# Roadmap configuration
project_name: "Test Project"
version: "1.0.0"
""")

        # Change to temp directory
        os.chdir(temp_path)

        try:
            yield temp_path
        finally:
            os.chdir(original_cwd)


# Centralized Common Fixtures
# ===========================


@pytest.fixture(scope="session")
def mock_core():
    """Create standardized mock RoadmapCore instance.

    This centralizes the mock_core fixture used across multiple test files.
    Individual tests can override specific behavior as needed.
    """
    return TestDataFactory.create_mock_core()


@pytest.fixture(scope="session")
def mock_config():
    """Create standardized mock RoadmapConfig instance."""
    return TestDataFactory.create_mock_config()


@pytest.fixture(scope="session")
def mock_issue():
    """Create standardized mock Issue instance."""
    return TestDataFactory.create_mock_issue()


@pytest.fixture(scope="session")
def mock_milestone():
    """Create standardized mock Milestone instance."""
    return TestDataFactory.create_mock_milestone()


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests that need filesystem operations.

    This centralizes the temp_dir fixture pattern used across multiple test files.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = Path.cwd()
        os.chdir(tmpdir)
        try:
            yield Path(tmpdir)
        finally:
            os.chdir(old_cwd)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace with initialized roadmap structure.

    This provides a more complete workspace setup for integration tests.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = Path.cwd()
        os.chdir(tmpdir)

        # Initialize basic roadmap structure
        roadmap_dir = Path(tmpdir) / ".roadmap"
        roadmap_dir.mkdir(exist_ok=True)
        (roadmap_dir / "issues").mkdir(exist_ok=True)
        (roadmap_dir / "milestones").mkdir(exist_ok=True)

        # Create basic config
        config_file = roadmap_dir / "config.yaml"
        config_file.write_text("""# Test Configuration
project_name: "Test Project"
version: "1.0.0"
""")

        try:
            yield Path(tmpdir)
        finally:
            os.chdir(old_cwd)


# GitHub and Webhook Testing Fixtures
# ===================================


@pytest.fixture
def github_webhook_payload():
    """Create GitHub webhook payload factory function."""
    return TestDataFactory.create_github_webhook_payload


@pytest.fixture
def webhook_signature_creator():
    """Create webhook signature factory function."""
    return TestDataFactory.create_webhook_signature


@pytest.fixture
def github_api_response():
    """Create GitHub API response factory function."""
    return TestDataFactory.create_github_api_response


@pytest.fixture
def cli_test_data():
    """Create CLI test data factory function."""
    return TestDataFactory.create_cli_test_data


# Performance-Optimized Fixtures
# ==============================


@pytest.fixture
def lightweight_mock_core():
    """Create lightweight mock core for performance-critical tests.

    This provides minimal mocking for tests that don't need full core functionality.
    """
    core = Mock()
    core.is_initialized.return_value = True
    core.get_issues.return_value = []
    return core


@pytest.fixture
def mock_github_client():
    """Mock GitHubClient for testing."""
    with patch("roadmap.sync.GitHubClient") as mock_client_class:
        mock_client = Mock()
        # Set up common methods and properties
        mock_client.is_authenticated = True
        mock_client.owner = "test-owner"
        mock_client.repo = "test-repo"
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def patch_github_integration():
    """Lightweight patch for GitHub integration to avoid heavy mocking.

    Note: enhanced_github_integration has been moved to future/ (post-1.0 feature).
    This fixture is kept for backward compatibility but returns a simple mock.
    """
    # Since EnhancedGitHubIntegration has been archived, we just create a simple mock
    from unittest.mock import Mock

    mock = Mock()
    mock.is_github_enabled.return_value = True
    mock.handle_push_event.return_value = []
    mock.handle_pull_request_event.return_value = []
    yield mock


@pytest.fixture
def temp_workspace_with_core():
    """Create temporary workspace with initialized roadmap and return both path and core.

    Returns tuple of (workspace_path, core_instance) for tests that need both.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = Path.cwd()
        os.chdir(tmpdir)

        # Initialize roadmap structure
        roadmap_dir = Path(tmpdir) / ".roadmap"
        roadmap_dir.mkdir(exist_ok=True)
        (roadmap_dir / "issues").mkdir(exist_ok=True)
        (roadmap_dir / "milestones").mkdir(exist_ok=True)

        # Create basic config
        config_file = roadmap_dir / "config.yaml"
        config_file.write_text("""# Test Configuration
project_name: "Test Project"
version: "1.0.0"
""")

        # Initialize roadmap core
        with patch("roadmap.core.RoadmapCore.initialize"):
            from roadmap.application.core import RoadmapCore

            core = RoadmapCore()
            core.is_initialized = Mock(return_value=True)

        try:
            yield Path(tmpdir), core
        finally:
            os.chdir(old_cwd)


@pytest.fixture(scope="session")
def session_temp_workspace(tmp_path_factory):
    """Session-scoped temporary workspace for reuse across tests.

    Major performance optimization: reuse workspace structure
    across multiple tests in the same session.
    """
    workspace = tmp_path_factory.mktemp("shared_workspace")

    # Create basic roadmap structure once
    roadmap_dir = workspace / ".roadmap"
    roadmap_dir.mkdir(exist_ok=True)
    (roadmap_dir / "issues").mkdir(exist_ok=True)
    (roadmap_dir / "milestones").mkdir(exist_ok=True)

    # Create basic config once
    config_file = roadmap_dir / "config.yaml"
    config_file.write_text("""# Session Test Configuration
project_name: "Session Test Project"
version: "1.0.0"
""")

    return workspace


@pytest.fixture(scope="session")
def session_mock_github_client():
    """Session-scoped GitHub client mock for performance."""
    mock_client = Mock()
    mock_client.is_authenticated = True
    mock_client.owner = "test-owner"
    mock_client.repo = "test-repo"
    mock_client.get_issues.return_value = []
    mock_client.get_milestones.return_value = []
    return mock_client


@pytest.fixture
def patch_filesystem_operations():
    """Patch heavy filesystem operations for faster tests."""
    with (
        patch("roadmap.core.RoadmapCore.initialize") as mock_init,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.write_text") as mock_write,
    ):
        mock_init.return_value = True
        mock_mkdir.return_value = None
        mock_write.return_value = None

        yield {"init": mock_init, "mkdir": mock_mkdir, "write_text": mock_write}


# Performance Test Utilities
# ==========================


@pytest.fixture(scope="session")
def shared_git_repo(tmp_path_factory):
    """Session-scoped git repository for reuse across slow tests.

    Major performance optimization: creates git repo once per session,
    copies for tests that need isolation.
    """
    import subprocess

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
    """
    import shutil

    repo_copy = tmp_path / "git_repo_copy"
    shutil.copytree(shared_git_repo, repo_copy)
    return repo_copy


@pytest.fixture(scope="session")
def performance_test_config():
    """Configuration for performance-optimized tests."""
    return {
        "enable_mocking": True,
        "skip_filesystem": True,
        "mock_git_operations": True,
        "lightweight_fixtures": True,
    }


@pytest.fixture
def fast_mock_core():
    """Ultra-lightweight mock core with minimal setup."""
    core = Mock()
    core.is_initialized.return_value = True
    core.workspace_root = Path("/tmp/fast_test")
    core.get_issues.return_value = []
    core.get_milestones.return_value = []
    return core


@pytest.fixture
def mock_git_operations():
    """Mock non-essential git operations for performance.

    Selectively mocks git operations that don't affect core hook testing.
    Major performance optimization for integration tests.

    Note: repository_scanner has been moved to future/ (post-1.0 feature).
    This fixture is kept for backward compatibility.
    """
    # Since repository_scanner has been archived, just return an empty mock dict
    yield {"scan_commit_history": Mock(), "scan_branch_history": Mock()}


@pytest.fixture
def selective_git_mock():
    """Selectively mock only expensive git operations.

    Keeps essential git operations real for integration testing,
    mocks only the performance bottlenecks.
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


def pytest_collection_modifyitems(config, items):
    """Add performance optimizations based on test markers."""
    for item in items:
        # Mark slow tests automatically based on patterns
        if any(
            pattern in item.nodeid
            for pattern in [
                "git_hooks_integration",
                "test_multi_branch_workflow",
                "test_hook_performance",
                "repository_scanner_integration",
                "test_complete_roadmap_lifecycle",
            ]
        ):
            item.add_marker(pytest.mark.slow)

        # Add integration marker for heavy tests
        if "integration" in item.nodeid.lower() and not item.get_closest_marker("unit"):
            item.add_marker(pytest.mark.integration)

        # Add performance optimization markers
        if "git_hooks_integration" in item.nodeid:
            item.add_marker(pytest.mark.performance)

        # Auto-apply optimized fixtures for slow tests (but not integration tests)
        if item.get_closest_marker("slow") and "repository_scanner" in item.nodeid:
            # Skip mocking for integration tests that need real repository scanning
            if not item.get_closest_marker("integration"):
                # Add selective mocking marker for repository scanner tests
                item.add_marker(pytest.mark.mock_scanning)
