"""Integration test for git hooks functionality."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from roadmap.adapters.git.hook_installer import HookInstaller


@pytest.mark.integration
class TestGitHooksIntegration:
    """Integration tests for git hooks."""

    def test_hook_script_executes_without_error(self, temp_dir_context):
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

                # Create and install hooks using HookInstaller
                installer = HookInstaller(hooks_dir)
                installer.install(["post-commit"])

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

    def test_all_hooks_install_without_errors(self, temp_dir_context):
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
                installer = HookInstaller(hooks_dir)

                # Install all available hooks
                hook_names = ["post-commit", "pre-push", "post-merge", "post-checkout"]

                result = installer.install(hook_names)
                assert result is True, "All hooks should install successfully"

                for hook_name in hook_names:
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
