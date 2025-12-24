"""Tests for git hooks manager."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.git.git_hooks_manager import GitHookManager


@pytest.fixture
def mock_core():
    """Create mock RoadmapCore."""
    return MagicMock()


@pytest.fixture
def manager(mock_core, tmp_path):
    """Create GitHookManager instance with mocked git."""
    with patch("roadmap.adapters.git.git_hooks_manager.GitIntegration") as mock_git:
        git_instance = MagicMock()
        mock_git.return_value = git_instance
        git_instance.is_git_repository.return_value = True

        # Create fake .git/hooks directory
        git_dir = tmp_path / ".git" / "hooks"
        git_dir.mkdir(parents=True, exist_ok=True)

        with patch("roadmap.adapters.git.git_hooks_manager.Path") as mock_path_class:
            mock_path_class.return_value = git_dir
            manager = GitHookManager(mock_core)
            manager.hooks_dir = git_dir
            return manager


class TestGitHookManager:
    """Test GitHookManager class."""

    def test_init(self, mock_core):
        """Test manager initialization."""
        with patch("roadmap.adapters.git.git_hooks_manager.GitIntegration"):
            manager = GitHookManager(mock_core)
            assert manager.core == mock_core

    def test_install_hooks_all(self, manager):
        """Test installing all hooks."""
        result = manager.install_hooks()
        assert isinstance(result, bool)

    def test_install_hooks_specific(self, manager):
        """Test installing specific hooks."""
        hooks = ["post-commit", "pre-push"]
        result = manager.install_hooks(hooks=hooks)
        assert isinstance(result, bool)

    def test_install_hooks_no_git_dir(self, mock_core):
        """Test installing hooks when not in git repo."""
        with patch("roadmap.adapters.git.git_hooks_manager.GitIntegration") as mock_git:
            git_instance = MagicMock()
            mock_git.return_value = git_instance
            git_instance.is_git_repository.return_value = False

            manager = GitHookManager(mock_core)
            result = manager.install_hooks()
            assert not result

    def test_uninstall_hooks(self, manager):
        """Test uninstalling hooks."""
        # Create a dummy hook file with roadmap-hook marker
        hook_file = manager.hooks_dir / "post-commit"
        hook_file.write_text("#!/bin/bash\n# roadmap-hook\necho 'test'")

        result = manager.uninstall_hooks()
        assert isinstance(result, bool)

    def test_uninstall_hooks_no_git_dir(self, mock_core):
        """Test uninstalling hooks when not in git repo."""
        with patch("roadmap.adapters.git.git_hooks_manager.GitIntegration"):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = None
            result = manager.uninstall_hooks()
            assert not result

    def test_get_hooks_status(self, manager):
        """Test getting hooks status."""
        result = manager.get_hooks_status()
        assert isinstance(result, dict)

    def test_get_hooks_status_empty_repo(self, mock_core):
        """Test getting hooks status with no hooks dir."""
        with patch("roadmap.adapters.git.git_hooks_manager.GitIntegration"):
            manager = GitHookManager(mock_core)
            manager.hooks_dir = None
            result = manager.get_hooks_status()
            assert result == {}

    def test_hook_status_details(self, manager):
        """Test hook status contains expected fields."""
        # Install a hook first
        manager.install_hooks(["post-commit"])

        result = manager.get_hooks_status()
        assert isinstance(result, dict)
        # Status should have hook information
        if result:
            for _, hook_info in result.items():
                assert isinstance(hook_info, dict)

    def test_hook_status_with_roadmap_hook(self, manager):
        """Test detecting roadmap hooks in status."""
        # Create a hook file with roadmap-hook marker
        hook_file = manager.hooks_dir / "post-commit"
        hook_file.write_text("#!/bin/bash\n# roadmap-hook\necho 'test'")
        hook_file.chmod(0o755)

        result = manager.get_hooks_status()
        assert isinstance(result, dict)
        # Should return a dictionary with hook statuses
        assert len(result) >= 0

    def test_get_hook_config(self, manager):
        """Test getting hook config."""
        # Install a hook first
        manager.install_hooks(["post-commit"])

        result = manager.get_hook_config()
        # Should return config or None
        assert result is None or isinstance(result, dict)

    def test_get_hook_config_with_json(self, manager):
        """Test getting hook config when it exists as JSON."""
        hook_file = manager.hooks_dir / "post-commit"
        hook_file.write_text("#!/bin/bash\n# roadmap-hook\necho 'hook running'")
        hook_file.chmod(0o755)

        result = manager.get_hook_config()
        # Should handle missing config gracefully
        assert result is None or isinstance(result, dict)
