"""Integration test for git hooks functionality."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from roadmap.adapters.git.git_hooks_manager import GitHookManager
from roadmap.infrastructure.core import RoadmapCore


@pytest.mark.integration
class TestGitHooksIntegration:
    """Integration tests for git hooks."""

    def test_hook_script_executes_without_error(self):
        """Test that generated hook script can be executed without errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)

            # Create a minimal roadmap setup
            roadmap_dir = repo_path / ".roadmap"
            roadmap_dir.mkdir(exist_ok=True)
            (roadmap_dir / "issues").mkdir(exist_ok=True)
            (roadmap_dir / "milestones").mkdir(exist_ok=True)

            # Save original cwd
            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)

                # Initialize roadmap core
                core = RoadmapCore()

                # Create and install hooks
                manager = GitHookManager(core)
                manager.hooks_dir = hooks_dir
                manager._install_hook("post-commit")

                # Verify hook file exists and is executable
                hook_file = hooks_dir / "post-commit"
                assert hook_file.exists(), "Hook file should be created"
                assert hook_file.stat().st_mode & 0o111, "Hook should be executable"

                # Test that the hook script can be parsed by bash
                result = subprocess.run(
                    ["bash", "-n", str(hook_file)],  # -n flag: syntax check only
                    capture_output=True,
                    text=True,
                )
                assert (
                    result.returncode == 0
                ), f"Hook has bash syntax errors: {result.stderr}"

            finally:
                os.chdir(original_cwd)

    def test_hook_handler_execution_with_real_git_repo(self):
        """Test hook handler execution in a real git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            original_cwd = os.getcwd()

            try:
                os.chdir(repo_path)

                # Initialize git repository
                subprocess.run(["git", "init"], check=True, capture_output=True)
                subprocess.run(
                    ["git", "config", "user.name", "Test User"],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "config", "user.email", "test@example.com"],
                    check=True,
                    capture_output=True,
                )

                # Initialize roadmap
                core = RoadmapCore()
                core.initialize()

                # Install hooks
                manager = GitHookManager(core)
                manager.install_hooks(hooks=["post-commit"])

                # Create a test commit
                test_file = repo_path / "test.txt"
                test_file.write_text("test content")
                subprocess.run(
                    ["git", "add", "test.txt"], check=True, capture_output=True
                )

                # Try to commit - the post-commit hook should run
                result = subprocess.run(
                    ["git", "commit", "-m", "Test commit"],
                    capture_output=True,
                    text=True,
                )

                # The commit should succeed (hook failures should be silent)
                assert result.returncode == 0, f"Git commit failed: {result.stderr}"

                # Verify the commit was created
                log_result = subprocess.run(
                    ["git", "log", "--oneline"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                assert "Test commit" in log_result.stdout

            finally:
                os.chdir(original_cwd)

    def test_all_hooks_install_without_errors(self):
        """Test that all hook types can be installed without errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            hooks_dir = repo_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)

            # Create minimal roadmap setup
            roadmap_dir = repo_path / ".roadmap"
            roadmap_dir.mkdir(exist_ok=True)
            (roadmap_dir / "issues").mkdir(exist_ok=True)
            (roadmap_dir / "milestones").mkdir(exist_ok=True)

            original_cwd = os.getcwd()
            try:
                os.chdir(repo_path)
                core = RoadmapCore()
                manager = GitHookManager(core)
                manager.hooks_dir = hooks_dir

                # Install all available hooks
                hook_names = ["post-commit", "pre-push", "post-merge", "post-checkout"]

                for hook_name in hook_names:
                    manager._install_hook(hook_name)

                    hook_file = hooks_dir / hook_name
                    assert hook_file.exists(), f"Hook {hook_name} should be created"

                    # Check syntax
                    result = subprocess.run(
                        ["bash", "-n", str(hook_file)],
                        capture_output=True,
                        text=True,
                    )
                    assert (
                        result.returncode == 0
                    ), f"Hook {hook_name} has syntax errors: {result.stderr}"

            finally:
                os.chdir(original_cwd)
