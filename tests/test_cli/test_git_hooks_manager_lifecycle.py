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
