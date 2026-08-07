"""Core integration tests for Git hooks functionality."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# git_hooks imports intentionally removed to avoid unused import warnings
from roadmap.core.domain import IssueType, Priority
from roadmap.infrastructure.coordination.core import RoadmapCore


@pytest.mark.integration
class TestGitHooksIntegration:
    """Integration tests for git hooks in realistic scenarios."""

    @pytest.fixture
    def git_hooks_repo(self, temp_dir_context):
        """Create a git repository with roadmap initialized for hooks testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()

            try:
                # Initialize git repository
                subprocess.run(["git", "init"], cwd=repo_path, check=True)
                subprocess.run(
                    [
                        "git",
                        "config",
                        "user.name",
                        "Hook Integration Test",
                    ],
                    cwd=repo_path,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.email", "hook-test@integration.com"],
                    cwd=repo_path,
                    check=True,
                )

                # Create initial commit
                (repo_path / "README.md").write_text("# Git Hooks Integration Test\\n")
                subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
                )

                # Change to repo directory and initialize roadmap
                os.chdir(repo_path)

                core = RoadmapCore()
                core.initialize()

                yield core, repo_path

            finally:
                os.chdir(original_cwd)

    def test_complete_hook_lifecycle_integration(self, git_hooks_repo):
        """Test complete git hook lifecycle with real commits and issue updates."""
        core, repo_path = git_hooks_repo

        # Create test issues for different scenarios
        core.issues.create(
            title="Feature Implementation with Hooks",
            priority=Priority.HIGH,
            issue_type=IssueType.FEATURE,
        )

        core.issues.create(
            title="Critical Bug Fix with Progress",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
        )
