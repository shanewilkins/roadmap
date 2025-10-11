"""Global test configuration and fixtures."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_roadmap_workspace():
    """Isolate each test with its own temporary roadmap workspace.
    
    This fixture automatically runs for every test to prevent test pollution
    by ensuring each test starts with a clean environment.
    """
    # Store original state
    original_cwd = os.getcwd()
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
        os.chdir(original_cwd)
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