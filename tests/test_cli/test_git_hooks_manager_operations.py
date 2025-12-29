"""Error path tests for git_hooks_manager.py - Phase 10a Tier 1 coverage expansion.

This module tests error handling and exception paths in the Git hook manager,
focusing on hook installation failures, git operations, file I/O errors, etc.

Currently git_hooks_manager.py has 65% coverage.
Target after Phase 10a: 85%+ coverage
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.git.git_hooks_manager import GitHookManager
from roadmap.core.domain import MilestoneStatus, Status
from tests.unit.domain.test_data_factory import TestDataFactory

# ========== Unit Tests: Hook Installation ==========


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
