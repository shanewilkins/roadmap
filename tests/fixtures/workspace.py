"""Workspace isolation and temporary directory fixtures.

Provides fixtures for creating and managing isolated test workspaces,
temporary directories, and roadmap structure setup.
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="function")
def isolate_roadmap_workspace(request, tmp_path):
    """Isolate each test in a temporary directory unless it's marked as unit test.

    PERFORMANCE OPTIMIZATION:
    - Skip isolation for unit tests (marked with @pytest.mark.unit) - major performance win
    - For integration tests, change to a temp directory to isolate .roadmap artifacts
    - This prevents parallel test workers from polluting each other's data
    """
    # Skip isolation for unit tests - major performance win
    if hasattr(request.node, "get_closest_marker"):
        if request.node.get_closest_marker("unit"):
            yield
            return

    # Store original state
    try:
        original_cwd = os.getcwd()
    except (FileNotFoundError, OSError):
        # If current directory doesn't exist, use root as fallback
        original_cwd = "/tmp"
        os.chdir(original_cwd)

    original_env = os.environ.copy()

    try:
        # For integration tests, change to temp directory to isolate .roadmap
        # This prevents parallel workers from sharing .roadmap artifacts
        test_temp_dir = tmp_path / f"test_{request.node.name}"
        test_temp_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(str(test_temp_dir))

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

    Returns:
        Path to the temporary workspace directory
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


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests that need filesystem operations.

    This centralizes the temp_dir fixture pattern used across multiple test files.

    Returns:
        Path object for temporary directory
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

    Returns:
        Path object for temporary workspace with .roadmap structure
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = Path.cwd()
        os.chdir(tmpdir)

        # Use the CLI runner to properly initialize the workspace
        from click.testing import CliRunner

        from roadmap.adapters.cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to initialize temp_workspace: {result.output}")

        try:
            yield Path(tmpdir)
        finally:
            os.chdir(old_cwd)


@pytest.fixture(scope="session")
def session_temp_workspace(tmp_path_factory):
    """Session-scoped temporary workspace for reuse across tests.

    Major performance optimization: reuse workspace structure
    across multiple tests in the same session.

    Returns:
        Path object for session-scoped workspace
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
