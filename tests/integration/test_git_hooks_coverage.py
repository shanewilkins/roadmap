"""Additional focused git hooks tests to improve coverage."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.git.git_hooks import GitHookManager
from roadmap.infrastructure.coordination.core import RoadmapCore


class TestGitHooksSpecificCoverage:
    """Focused tests to cover specific git hooks functionality."""

    @pytest.fixture
    def minimal_git_repo(self):
        """Create minimal git repository for focused testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()

            try:
                # Initialize git repository
                subprocess.run(
                    ["git", "init"], cwd=repo_path, check=True, capture_output=True
                )
                subprocess.run(
                    ["git", "config", "user.name", "Test"], cwd=repo_path, check=True
                )
                subprocess.run(
                    ["git", "config", "user.email", "test@test.com"],
                    cwd=repo_path,
                    check=True,
                )

                # Create initial commit
                (repo_path / "README.md").write_text("# Test\\n")
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

    def test_hook_manager_without_git_repo(self):
        """Test GitHookManager behavior outside git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)  # Non-git directory

                # This should fail gracefully since we're not in a git repo
                core = RoadmapCore()
                hook_manager = GitHookManager(core)

                # Should detect no git repository
                assert hook_manager.hooks_dir is None

                # Install hooks should fail gracefully
                assert not hook_manager.install_hooks()

                # Uninstall hooks should fail gracefully
                assert not hook_manager.uninstall_hooks()

            finally:
                os.chdir(original_cwd)

    def test_hook_manager_install_specific_hooks(self, minimal_git_repo):
        """Test installing specific hooks only."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)

        # Install only specific hooks
        result = hook_manager.install_hooks(["post-commit", "pre-push"])
        assert result

        hooks_dir = repo_path / ".git" / "hooks"

        # Should have installed requested hooks
        assert (hooks_dir / "post-commit").exists()
        assert (hooks_dir / "pre-push").exists()

        # Should not have installed other hooks
        assert not (hooks_dir / "post-checkout").exists()
        assert not (hooks_dir / "post-merge").exists()

    def test_hook_manager_install_invalid_hooks(self, minimal_git_repo):
        """Test installing invalid hook names."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)

        # Install mix of valid and invalid hooks
        result = hook_manager.install_hooks(["post-commit", "invalid-hook", "pre-push"])
        assert result  # Should still succeed for valid hooks

        hooks_dir = repo_path / ".git" / "hooks"

        # Should have installed valid hooks
        assert (hooks_dir / "post-commit").exists()
        assert (hooks_dir / "pre-push").exists()

        # Should not have created invalid hook
        assert not (hooks_dir / "invalid-hook").exists()

    def test_uninstall_hooks_non_roadmap_hooks(self, minimal_git_repo):
        """Test uninstalling when non-roadmap hooks exist."""
        core, repo_path = minimal_git_repo

        hooks_dir = repo_path / ".git" / "hooks"

        # Create a non-roadmap hook
        non_roadmap_hook = hooks_dir / "post-commit"
        non_roadmap_hook.write_text('#!/bin/bash\\necho "Non-roadmap hook"\\n')
        non_roadmap_hook.chmod(0o755)

        hook_manager = GitHookManager(core)

        # Uninstall should not remove non-roadmap hooks
        result = hook_manager.uninstall_hooks()
        assert result

        # Non-roadmap hook should still exist
        assert non_roadmap_hook.exists()
        assert "roadmap-hook" not in non_roadmap_hook.read_text()

    @patch("subprocess.run")
    def test_handle_post_commit_no_latest_commit(
        self, mock_subprocess, minimal_git_repo
    ):
        """Test post-commit handler when no latest commit available."""
        core, repo_path = minimal_git_repo

        # Mock git command to return empty
        mock_subprocess.return_value = Mock(
            stdout="", stderr="", returncode=0, check=True
        )

        hook_manager = GitHookManager(core)

        # Should handle gracefully when no commit SHA
        hook_manager.handle_post_commit()  # Should not raise exception
        assert True

    @patch("subprocess.run")
    def test_handle_pre_push_no_current_branch(self, mock_subprocess, minimal_git_repo):
        """Test pre-push handler when no current branch available."""
        core, repo_path = minimal_git_repo

        # Mock git command to return empty branch
        mock_subprocess.return_value = Mock(
            stdout="", stderr="", returncode=0, check=True
        )

        hook_manager = GitHookManager(core)

        # Should handle gracefully when no current branch
        hook_manager.handle_pre_push()  # Should not raise exception
        assert True

    def test_handle_post_checkout_no_git_integration(self, minimal_git_repo):
        """Test post-checkout handler behavior."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)

        # Should handle gracefully even without proper git integration setup
        hook_manager.handle_post_checkout()  # Should not raise exception
        assert True

    def test_handle_post_merge_behavior(self, minimal_git_repo):
        """Test post-merge handler behavior."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)

        # Should handle gracefully
        hook_manager.handle_post_merge()  # Should not raise exception
        assert True

    def test_hook_script_content_generation(self, minimal_git_repo):
        """Test that hook scripts are generated correctly."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)
        hook_manager.install_hooks(["post-commit"])

        hook_file = repo_path / ".git" / "hooks" / "post-commit"
        assert hook_file.exists()

        content = hook_file.read_text()

        # Verify hook script contains expected content
        assert "#!/bin/bash" in content
        assert "roadmap-hook" in content
        assert "GitHookManager" in content
        assert "post_commit" in content  # Method name used with getattr
        assert "getattr(hook_manager" in content  # Dynamic method calling
        assert "sys.path.insert(0" in content

    def test_hook_file_permissions(self, minimal_git_repo):
        """Test that installed hooks have correct permissions."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)
        hook_manager.install_hooks()

        hooks_dir = repo_path / ".git" / "hooks"
        hook_names = ["post-commit", "pre-push", "post-checkout", "post-merge"]

        for hook_name in hook_names:
            hook_file = hooks_dir / hook_name
            assert hook_file.exists()

            # Check that hook is executable
            stat_info = hook_file.stat()
            assert stat_info.st_mode & 0o111  # At least one execute bit set

    def test_hook_install_error_handling(self, minimal_git_repo):
        """Test hook installation error handling."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)

        # Make hooks directory read-only to cause installation error
        hooks_dir = repo_path / ".git" / "hooks"
        original_mode = hooks_dir.stat().st_mode

        try:
            os.chmod(hooks_dir, 0o444)  # Read-only

            # Installation should fail gracefully
            result = hook_manager.install_hooks()
            assert not result  # Should return False on error

        finally:
            # Restore original permissions
            os.chmod(hooks_dir, original_mode)

    def test_multiple_hook_install_uninstall_cycles(self, minimal_git_repo):
        """Test multiple install/uninstall cycles."""
        core, repo_path = minimal_git_repo

        hook_manager = GitHookManager(core)
        hooks_dir = repo_path / ".git" / "hooks"

        for _cycle in range(3):
            # Install hooks
            assert hook_manager.install_hooks()

            # Verify installation
            for hook_name in ["post-commit", "pre-push", "post-checkout", "post-merge"]:
                hook_file = hooks_dir / hook_name
                assert hook_file.exists()

            # Uninstall hooks
            assert hook_manager.uninstall_hooks()

            # Verify uninstallation (roadmap hooks should be removed)
            for hook_name in ["post-commit", "pre-push", "post-checkout", "post-merge"]:
                hook_file = hooks_dir / hook_name
                if hook_file.exists():
                    content = hook_file.read_text()
                    assert "roadmap-hook" not in content
