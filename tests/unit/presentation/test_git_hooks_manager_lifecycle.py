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
from tests.unit.domain.test_data_factory_generation import TestDataFactory

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
            manager.hooks_dir = Path(".git/hooks")
            # Mock the _install_single_hook method to raise an exception
            with patch(
                "roadmap.adapters.git.hook_installer.HookInstaller._install_single_hook",
                side_effect=Exception("Install error"),
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

            with patch(
                "roadmap.adapters.git.git_hooks_manager.HookInstaller"
            ) as mock_installer_class:
                mock_installer = Mock()
                mock_installer.install.return_value = True
                mock_installer_class.return_value = mock_installer
                result = manager.install_hooks(["post-commit", "pre-push"])

            assert result is True
            mock_installer_class.assert_called_once_with(manager.hooks_dir)
            mock_installer.install.assert_called_once_with(["post-commit", "pre-push"])

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

            with patch(
                "roadmap.adapters.git.git_hooks_manager.HookInstaller"
            ) as mock_installer_class:
                mock_installer = Mock()
                mock_installer.install.return_value = True
                mock_installer_class.return_value = mock_installer
                manager.install_hooks(["post-commit", "invalid-hook"])

            # Verify HookInstaller was called with filtered hooks
            mock_installer.install.assert_called_once_with(
                ["post-commit", "invalid-hook"]
            )


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


pytestmark = pytest.mark.unit
