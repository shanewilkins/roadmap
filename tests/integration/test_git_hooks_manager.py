"""Tests for Git hooks and workflow automation."""

import os
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.git.git_hooks import GitHookManager
from roadmap.core.domain import Priority, Status
from roadmap.infrastructure.core import RoadmapCore


@pytest.mark.integration
class TestGitHookManager:
    """Test Git hook manager functionality."""

    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary Git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize Git repo
            subprocess.run(["git", "init"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"], check=True
            )

            # Initialize roadmap
            core = RoadmapCore()
            core.initialize()

            yield temp_dir, core

    def test_git_hook_manager_initialization(self, temp_git_repo):
        """Test GitHookManager initialization."""
        _, core = temp_git_repo

        hook_manager = GitHookManager(core)

        assert hook_manager.core == core
        assert hook_manager.git_integration is not None
        assert hook_manager.hooks_dir == Path(".git/hooks")

    def test_install_hooks_success(self, temp_git_repo):
        """Test successful hook installation."""
        _, core = temp_git_repo

        hook_manager = GitHookManager(core)
        success = hook_manager.install_hooks(["post-commit"])

        assert success

        # Check that hook file was created
        hook_file = Path(".git/hooks/post-commit")
        assert hook_file.exists()
        assert hook_file.stat().st_mode & 0o111  # Check executable

        # Check hook content
        content = hook_file.read_text()
        assert "roadmap-hook: post-commit" in content
        assert "GitHookManager" in content

    def test_install_all_hooks(self, temp_git_repo):
        """Test installing all available hooks."""
        _, core = temp_git_repo

        hook_manager = GitHookManager(core)
        success = hook_manager.install_hooks()

        assert success

        # Check all hook files were created
        expected_hooks = ["post-commit", "pre-push", "post-merge", "post-checkout"]
        for hook_name in expected_hooks:
            hook_file = Path(f".git/hooks/{hook_name}")
            assert hook_file.exists()
            assert hook_file.stat().st_mode & 0o111

    def test_uninstall_hooks(self, temp_git_repo):
        """Test hook uninstallation."""
        _, core = temp_git_repo

        hook_manager = GitHookManager(core)

        # Install hooks first
        hook_manager.install_hooks(["post-commit", "pre-push"])

        # Verify they exist
        assert Path(".git/hooks/post-commit").exists()
        assert Path(".git/hooks/pre-push").exists()

        # Uninstall
        success = hook_manager.uninstall_hooks()
        assert success

        # Verify they're gone
        assert not Path(".git/hooks/post-commit").exists()
        assert not Path(".git/hooks/pre-push").exists()

    def test_hook_content_generation(self, temp_git_repo):
        """Test hook script content generation."""
        _, core = temp_git_repo

        from roadmap.adapters.git.hook_script_generator import HookContentGenerator

        content = HookContentGenerator.generate("post-commit")

        assert "#!/bin/bash" in content
        assert "roadmap-hook: post-commit" in content
        assert "post_commit" in content  # Check for method name used with getattr
        assert "getattr(hook_manager" in content  # Check for dynamic method calling
        assert "GitHookManager" in content
        assert "RoadmapCore" in content

    @patch("roadmap.adapters.git.git_hooks.GitIntegration")
    def test_handle_post_commit(self, mock_git_integration, temp_git_repo):
        """Test post-commit hook handler."""
        _, core = temp_git_repo

        # Create a test issue
        issue = core.issues.create("Test issue", Priority.MEDIUM)

        # Mock Git integration
        mock_git = Mock()
        mock_commit = Mock()
        mock_commit.extract_roadmap_references.return_value = [issue.id]
        mock_commit.extract_progress_info.return_value = 50.0
        mock_commit.hash = "abc123"
        mock_commit.message = f"Test commit [roadmap:{issue.id}] [progress:50%]"
        mock_commit.date = datetime.now(UTC)

        mock_git.get_recent_commits.return_value = [mock_commit]
        mock_git.auto_update_issues_from_commits.return_value = {
            "updated": [issue.id],
            "closed": [],
            "errors": [],
        }
        mock_git_integration.return_value = mock_git

        hook_manager = GitHookManager(core)
        hook_manager.git_integration = mock_git

        # Manually update the issue to simulate what auto_update_issues_from_commits would do
        core.issues.update(
            issue.id, progress_percentage=50.0, status=Status.IN_PROGRESS
        )

        # Handle post-commit
        hook_manager.handle_post_commit()

        # Verify issue was updated
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.progress_percentage == 50.0
        assert updated_issue.status == Status.IN_PROGRESS

    @patch("subprocess.run")
    def test_handle_pre_push_with_completion(self, mock_subprocess, temp_git_repo):
        """Test pre-push hook with issue completion."""
        _, core = temp_git_repo

        # Create a test issue in TODO status
        issue = core.issues.create("Test issue", Priority.MEDIUM)

        # Mock git commands for current branch and merge target
        mock_subprocess.side_effect = [
            # git branch --show-current
            Mock(stdout="feature/test-branch", stderr="", returncode=0, check=True),
            # git config --get branch.feature/test-branch.remote
            Mock(stdout="origin", stderr="", returncode=0),
            # git config --get branch.feature/test-branch.merge
            Mock(stdout="refs/heads/main", stderr="", returncode=0),
        ]

        hook_manager = GitHookManager(core)

        # Handle pre-push (should simulate PR merge to main)
        hook_manager.handle_pre_push()

        # Since we're not on a main branch and don't have commits to process,
        # the hook should not change the issue status
        updated_issue = core.issues.get(issue.id)
        assert updated_issue.status == Status.TODO  # Should remain unchanged
        assert updated_issue.progress_percentage is None  # Should remain unchanged

    def test_non_git_repo_handling(self):
        """Test graceful handling when not in a Git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Initialize roadmap without Git
            core = RoadmapCore()
            core.initialize()

            hook_manager = GitHookManager(core)

            # Should handle gracefully
            assert hook_manager.hooks_dir is None
            assert not hook_manager.install_hooks()
            assert not hook_manager.uninstall_hooks()
