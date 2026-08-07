"""Error handling and recovery tests for Git hooks functionality."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from roadmap.adapters.git.git_hooks import GitHookManager
from roadmap.core.domain import IssueType, Priority
from roadmap.infrastructure.coordination.core import RoadmapCore


class TestGitHooksErrorRecovery:
    """Test git hooks error handling and recovery scenarios."""

    @pytest.fixture
    def corrupted_repo(self, temp_dir_context):
        """Create a git repository with potential corruption scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()

            try:
                # Initialize git repository
                subprocess.run(["git", "init"], cwd=repo_path, check=True)
                subprocess.run(
                    ["git", "config", "user.name", "Corruption Test"],
                    cwd=repo_path,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.email", "corrupt@test.com"],
                    cwd=repo_path,
                    check=True,
                )

                # Create initial commit
                (repo_path / "README.md").write_text("# Corruption Test\\n")
                subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
                )

                os.chdir(repo_path)

                core = RoadmapCore()
                core.initialize()

                yield core, repo_path

            finally:
                os.chdir(original_cwd)

    def test_hook_recovery_from_roadmap_corruption(self, corrupted_repo):
        """Test hook behavior when roadmap data is corrupted."""
        core, repo_path = corrupted_repo

        # Create and install hooks normally
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        # Create a test issue
        core.issues.create(
            title="Corruption Recovery Test",
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
        )

        issues = core.issues.list()
        issue_id = issues[0].id

        # Simulate roadmap data corruption by corrupting the issues file
        roadmap_dir = repo_path / ".roadmap"
        issues_dir = roadmap_dir / "issues"

        if issues_dir.exists():
            # Corrupt the issue file
            for issue_file in issues_dir.glob("*.md"):
                issue_file.write_text("CORRUPTED DATA\\n")

        # Try to make commits - hooks should not crash git operations
        test_file = repo_path / "recovery_test.py"
        test_file.write_text("# Recovery test\\n")
        subprocess.run(["git", "add", "recovery_test.py"], cwd=repo_path, check=True)

        # This should succeed even with corrupted roadmap data
        result = subprocess.run(
            ["git", "commit", "-m", f"{issue_id}: Recovery test commit"],
            cwd=repo_path,
            check=False,
        )

        # Git commit should succeed (hooks fail silently)
        assert result.returncode == 0

    def test_hook_recovery_from_missing_roadmap(self, corrupted_repo):
        """Test hook behavior when roadmap is completely missing."""
        core, repo_path = corrupted_repo

        # Install hooks first
        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        # Remove entire .roadmap directory
        roadmap_dir = repo_path / ".roadmap"
        if roadmap_dir.exists():
            shutil.rmtree(roadmap_dir)

        # Try to make commits - should not crash
        test_file = repo_path / "missing_roadmap_test.py"
        test_file.write_text("# Missing roadmap test\\n")
        subprocess.run(
            ["git", "add", "missing_roadmap_test.py"], cwd=repo_path, check=True
        )

        result = subprocess.run(
            ["git", "commit", "-m", "TEST123: Test with missing roadmap"],
            cwd=repo_path,
            check=False,
        )

        # Should succeed
        assert result.returncode == 0

    def test_hook_recovery_from_permission_errors(self, corrupted_repo):
        """Test hook behavior with permission errors."""
        core, repo_path = corrupted_repo

        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        # Create issue and make roadmap directory read-only
        core.issues.create(
            title="Permission Error Test",
            priority=Priority.MEDIUM,
            issue_type=IssueType.OTHER,
        )

        issues = core.issues.list()
        issue_id = issues[0].id

        # Make .roadmap directory read-only
        roadmap_dir = repo_path / ".roadmap"
        if roadmap_dir.exists():
            os.chmod(roadmap_dir, 0o444)

        try:
            # Try to make commits
            test_file = repo_path / "permission_test.py"
            test_file.write_text("# Permission test\\n")
            subprocess.run(
                ["git", "add", "permission_test.py"], cwd=repo_path, check=True
            )

            result = subprocess.run(
                ["git", "commit", "-m", f"{issue_id}: Permission test commit"],
                cwd=repo_path,
                check=False,
            )

            # Should succeed despite permission errors
            assert result.returncode == 0

        finally:
            # Restore permissions
            if roadmap_dir.exists():
                os.chmod(roadmap_dir, 0o755)
