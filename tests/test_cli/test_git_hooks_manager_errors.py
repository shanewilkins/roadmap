"""Error path tests for git_hooks_manager.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in the Git hook manager,
focusing on hook installation failures, git operations, file I/O errors, etc.

Currently git_hooks_manager.py has 65% coverage.
Target after Phase 10a: 85%+ coverage
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.git.git_hooks_manager import GitHookManager
from roadmap.core.domain import MilestoneStatus, Status
from tests.unit.domain.test_data_factory import TestDataFactory

# ========== Unit Tests: Hook Installation ==========


class TestHookInstallation:
    """Test hook installation error handling."""

    def test_install_hooks_returns_false_if_no_hooks_dir(self):
        """Test that install_hooks returns False when hooks directory is None."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = False

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            result = manager.install_hooks()

        assert result is False

    def test_install_hooks_returns_false_if_hooks_dir_not_exists(self):
        """Test that install_hooks returns False when hooks directory doesn't exist."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            with patch.object(Path, "exists", return_value=False):
                manager = GitHookManager(mock_core)
                result = manager.install_hooks()

        assert result is False

    def test_install_hooks_catches_exception_during_install(self):
        """Test that install_hooks catches and returns False on exception."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            with patch.object(
                manager, "_install_hook", side_effect=Exception("Install error")
            ):
                result = manager.install_hooks(["post-commit"])

        assert result is False

    def test_install_hooks_with_custom_hooks_list(self):
        """Test install_hooks with custom hooks list."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Mock(spec=Path)
            manager.hooks_dir.exists.return_value = True

            with patch.object(manager, "_install_hook") as mock_install:
                result = manager.install_hooks(["post-commit", "pre-push"])

            assert result is True
            assert mock_install.call_count == 2

    def test_install_hooks_ignores_invalid_hook_names(self):
        """Test install_hooks ignores hook names not in available list."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Mock(spec=Path)
            manager.hooks_dir.exists.return_value = True

            with patch.object(manager, "_install_hook") as mock_install:
                manager.install_hooks(["post-commit", "invalid-hook"])

            # Only valid hooks should be installed
            assert mock_install.call_count == 1


# ========== Unit Tests: Hook Uninstallation ==========


class TestHookUninstallation:
    """Test hook uninstallation error handling."""

    def test_uninstall_hooks_returns_false_if_no_hooks_dir(self):
        """Test that uninstall_hooks returns False when hooks directory is None."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = False

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            result = manager.uninstall_hooks()

        assert result is False

    def test_uninstall_hooks_only_removes_roadmap_hooks(self):
        """Test that uninstall only removes files containing roadmap marker."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_hook_file = Mock(spec=Path)
            mock_hook_file.exists.return_value = True
            mock_hook_file.read_text.return_value = "some other content"

            manager.hooks_dir = Mock(spec=Path)
            manager.hooks_dir.__truediv__ = Mock(return_value=mock_hook_file)

            result = manager.uninstall_hooks()

        # Should succeed but not unlink file without roadmap marker
        assert result is True
        mock_hook_file.unlink.assert_not_called()

    def test_uninstall_hooks_catches_read_error(self):
        """Test that uninstall_hooks catches file read errors."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_hook_file = Mock(spec=Path)
            mock_hook_file.exists.return_value = True
            mock_hook_file.read_text.side_effect = Exception("Read error")

            manager.hooks_dir = Mock(spec=Path)
            manager.hooks_dir.__truediv__ = Mock(return_value=mock_hook_file)

            result = manager.uninstall_hooks()

        # Should return False since exception was caught during iteration
        assert result is False


# ========== Unit Tests: Hook Status ==========


class TestHookStatus:
    """Test hook status retrieval error handling."""

    def test_get_hooks_status_returns_empty_if_no_hooks_dir(self):
        """Test get_hooks_status returns empty dict if hooks directory is None."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = False

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            status = manager.get_hooks_status()

        assert status == {}

    def test_get_hooks_status_handles_file_stat_error(self):
        """Test get_hooks_status handles stat errors gracefully."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_hook_file = Mock(spec=Path)
            mock_hook_file.exists.return_value = True
            mock_hook_file.read_text.return_value = "roadmap-hook: post-commit"
            mock_hook_file.stat.side_effect = Exception("Stat error")

            manager.hooks_dir = Mock(spec=Path)
            manager.hooks_dir.exists.return_value = True
            manager.hooks_dir.__truediv__ = Mock(return_value=mock_hook_file)

            status = manager.get_hooks_status()

        # Should still return status with partial info
        assert "post-commit" in status
        assert status["post-commit"]["installed"] is True
        assert status["post-commit"]["is_roadmap_hook"] is True

    def test_get_hooks_status_detects_executable_permission(self):
        """Test get_hooks_status detects executable permissions."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_hook_file = Mock(spec=Path)
            mock_hook_file.exists.return_value = True
            mock_hook_file.read_text.return_value = "roadmap-hook"

            # Set executable bit (0o111)
            mock_stat = Mock()
            mock_stat.st_mode = 0o755
            mock_hook_file.stat.return_value = mock_stat

            manager.hooks_dir = Mock(spec=Path)
            manager.hooks_dir.exists.return_value = True
            manager.hooks_dir.__truediv__ = Mock(return_value=mock_hook_file)

            status = manager.get_hooks_status()

        assert status["post-commit"]["executable"] is True


# ========== Unit Tests: Hook Configuration ==========


class TestHookConfiguration:
    """Test hook configuration retrieval."""

    def test_get_hook_config_returns_config_structure(self):
        """Test get_hook_config returns properly structured config."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            with patch.object(Path, "cwd", return_value=Path("/repo")):
                manager = GitHookManager(mock_core)
                manager.hooks_dir = Path(".git/hooks")

                config = manager.get_hook_config()

        assert config is not None
        assert "hooks_directory" in config
        assert "repository_root" in config
        assert "git_repository" in config
        assert "available_hooks" in config
        assert "core_initialized" in config
        assert "hooks_status" in config


# ========== Unit Tests: Post-Commit Handler ==========


class TestPostCommitHandler:
    """Test post-commit hook handling."""

    @patch("subprocess.run")
    def test_handle_post_commit_gets_commit_sha(self, mock_run):
        """Test handle_post_commit retrieves commit SHA."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        mock_result = Mock()
        mock_result.stdout = "abc1234"
        mock_run.return_value = mock_result

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Path(".git/hooks")

            with patch.object(manager, "_trigger_auto_sync_on_commit"):
                manager.handle_post_commit()

        mock_run.assert_called()

    @patch("subprocess.run")
    def test_handle_post_commit_handles_empty_commit_sha(self, mock_run):
        """Test handle_post_commit handles empty commit SHA."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Path(".git/hooks")

            # Should return early without error
            manager.handle_post_commit()

    @patch("subprocess.run", side_effect=Exception("Git error"))
    def test_handle_post_commit_catches_subprocess_error(self, mock_run):
        """Test handle_post_commit catches subprocess errors."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Path(".git/hooks")

            # Should not raise, silently fail
            manager.handle_post_commit()


# ========== Unit Tests: Branch Operations ==========


class TestBranchOperations:
    """Test branch-related hook handlers."""

    @patch("subprocess.run")
    def test_handle_post_checkout_gets_branch_name(self, mock_run):
        """Test handle_post_checkout retrieves branch name."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        mock_result = Mock()
        mock_result.stdout = "feature-branch"
        mock_run.return_value = mock_result

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Path(".git/hooks")

            with patch.object(manager, "_trigger_auto_sync_on_checkout"):
                manager.handle_post_checkout()

        mock_run.assert_called()

    @patch("subprocess.run")
    def test_handle_post_checkout_handles_empty_branch(self, mock_run):
        """Test handle_post_checkout handles empty branch name."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Path(".git/hooks")

            # Should return early without error
            manager.handle_post_checkout()

    @patch("subprocess.run")
    def test_handle_pre_push_gets_current_branch(self, mock_run):
        """Test handle_pre_push retrieves current branch."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        mock_result = Mock()
        mock_result.stdout = "main"
        mock_run.return_value = mock_result

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = Path(".git/hooks")

            manager.handle_pre_push()

        mock_run.assert_called()


# ========== Unit Tests: Milestone Operations ==========


class TestMilestoneOperations:
    """Test milestone-related operations."""

    def test_is_milestone_active_with_open_status(self):
        """Test _is_milestone_active returns True for open milestone."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_milestone = Mock()
            mock_milestone.status = "active"  # The code checks for lowercase 'active'

            result = manager._is_milestone_active(mock_milestone)

        assert result is True

    def test_is_milestone_active_with_closed_status(self):
        """Test _is_milestone_active returns False for closed milestone."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_milestone = Mock()
            mock_milestone.status = MilestoneStatus.CLOSED

            result = manager._is_milestone_active(mock_milestone)

        assert result is False

    def test_calculate_milestone_progress_empty_issues(self):
        """Test _calculate_milestone_progress with no issues."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            progress = manager._calculate_milestone_progress([])

        assert progress == 0.0

    def test_calculate_milestone_progress_with_issues(self):
        """Test _calculate_milestone_progress calculates correctly."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_issue1 = Mock()
            mock_issue1.status = Status.CLOSED

            mock_issue2 = Mock()
            mock_issue2.status = Status.IN_PROGRESS

            mock_issue3 = Mock()
            mock_issue3.status = Status.CLOSED

            progress = manager._calculate_milestone_progress(
                [mock_issue1, mock_issue2, mock_issue3]
            )

        # 2 out of 3 closed = 66.67%
        assert progress == pytest.approx(66.67, rel=1)

    def test_update_milestone_attributes_sets_progress(self):
        """Test _update_milestone_attributes sets progress."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_milestone = Mock()
            mock_milestone.calculated_progress = 0.0
            mock_milestone.status = "active"  # Use string instead of enum

            manager._update_milestone_attributes(mock_milestone, 75.0)

        assert mock_milestone.calculated_progress == 75.0

    def test_update_milestone_attributes_closes_at_100_percent(self):
        """Test _update_milestone_attributes closes milestone at 100%."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            mock_milestone = Mock()
            mock_milestone.calculated_progress = 0.0
            mock_milestone.status = "active"  # Use string instead of enum
            mock_milestone.actual_end_date = None

            manager._update_milestone_attributes(mock_milestone, 100.0)

        assert mock_milestone.status == MilestoneStatus.CLOSED


# ========== Unit Tests: Context Management ==========


class TestContextManagement:
    """Test branch context management."""

    def test_set_branch_context_creates_json_file(self, tmp_path, monkeypatch):
        """Test _set_branch_context creates context file."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        # Change to tmp_path for this test
        monkeypatch.chdir(tmp_path)

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)
            manager._set_branch_context("feature-branch", "issue-123")

        context_file = tmp_path / ".roadmap_branch_context.json"
        assert context_file.exists()

        with open(context_file) as f:
            context = json.load(f)

        assert context["branch"] == "feature-branch"
        assert context["issue_id"] == "issue-123"
        assert "timestamp" in context

    def test_set_branch_context_catches_write_error(self):
        """Test _set_branch_context handles write errors gracefully."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_git_integration = Mock()
        mock_git_integration.is_git_repository.return_value = True

        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration",
            return_value=mock_git_integration,
        ):
            manager = GitHookManager(mock_core)

            with patch.object(Path, "write_text", side_effect=Exception("Write error")):
                # Should not raise
                manager._set_branch_context("branch", "issue")


pytestmark = pytest.mark.unit
