"""Unit tests for Git hooks management and workflow automation."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.git.git import GitCommit
from roadmap.adapters.git.git_hooks import GitHookManager, WorkflowAutomation

# mock_core fixture provided by tests.fixtures.mocks module
# Uses centralized mock_core_simple


@pytest.fixture
def mock_git_integration():
    """Create a mock GitIntegration instance."""
    git = Mock()
    git.is_git_repository.return_value = True
    git.get_recent_commits.return_value = []
    return git


@pytest.fixture
def hook_manager(mock_core, mock_git_integration):
    """Create a GitHookManager instance with mocked dependencies."""
    with patch(
        "roadmap.adapters.git.git_hooks.GitIntegration",
        return_value=mock_git_integration,
    ):
        manager = GitHookManager(mock_core)
        manager.hooks_dir = Path("/fake/.git/hooks")
        return manager


@pytest.fixture
def workflow_automation(mock_core, mock_git_integration):
    """Create a WorkflowAutomation instance with mocked dependencies."""
    with patch(
        "roadmap.adapters.git.git_hooks.GitIntegration",
        return_value=mock_git_integration,
    ):
        automation = WorkflowAutomation(mock_core)
        automation.git_integration = mock_git_integration
        return automation


@pytest.fixture
def sample_commit():
    """Create a sample GitCommit for testing."""
    return GitCommit(
        hash="abc123",
        message="closes roadmap:TEST-001 - Complete feature",
        date=datetime(2025, 1, 15, 10, 30),
        author="Test Author",
        files_changed=["file1.py", "file2.py"],
    )


class TestGitHookManagerInit:
    """Test GitHookManager initialization."""

    @pytest.mark.parametrize(
        "is_git_repo,expected_hooks_dir",
        [
            (True, Path(".git/hooks")),
            (False, None),
        ],
    )
    def test_init_variants(self, mock_core, is_git_repo, expected_hooks_dir):
        """Test initialization with different Git repository states."""
        with patch(
            "roadmap.adapters.git.git_hooks_manager.GitIntegration"
        ) as mock_git_class:
            mock_git = Mock()
            mock_git.is_git_repository.return_value = is_git_repo
            mock_git_class.return_value = mock_git

            manager = GitHookManager(mock_core)

            assert manager.core == mock_core
            assert manager.hooks_dir == expected_hooks_dir


class TestGitHookManagerInstall:
    """Test Git hook installation."""

    @pytest.mark.parametrize(
        "hooks_dir,dir_exists,hook_count,expected_result,scenario",
        [
            (Path("/fake/.git/hooks"), True, 4, True, "all_hooks"),
            (Path("/fake/.git/hooks"), True, 2, True, "specific_hooks"),
            (None, True, 0, False, "no_hooks_dir"),
            (Path("/fake/.git/hooks"), False, 0, False, "dir_not_exists"),
        ],
    )
    def test_install_hooks_variants(
        self, hook_manager, hooks_dir, dir_exists, hook_count, expected_result, scenario
    ):
        """Test installation with different states and configurations."""
        hook_manager.hooks_dir = hooks_dir

        with (
            patch("pathlib.Path.exists", return_value=dir_exists),
            patch("pathlib.Path.write_text") as mock_write,
            patch("pathlib.Path.chmod") as mock_chmod,
        ):
            if scenario == "specific_hooks":
                result = hook_manager.install_hooks(hooks=["post-commit", "pre-push"])
            else:
                result = hook_manager.install_hooks()

            assert result is expected_result
            if expected_result:
                assert mock_write.call_count == hook_count
                assert mock_chmod.call_count == hook_count
                for call_args in mock_chmod.call_args_list:
                    assert call_args[0][0] == 0o755

    def test_install_hooks_exception(self, hook_manager):
        """Test installation fails gracefully on exception."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.write_text", side_effect=PermissionError("No access")),
        ):
            result = hook_manager.install_hooks()

            assert not result


class TestGitHookManagerUninstall:
    """Test Git hook uninstallation."""

    def test_uninstall_hooks_success(self, hook_manager):
        """Test successful uninstallation of roadmap hooks."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="#!/bin/bash\n# roadmap-hook"),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            result = hook_manager.uninstall_hooks()

            assert result
            # Should unlink 4 hooks
            assert mock_unlink.call_count == 4

    def test_uninstall_hooks_no_hooks_dir(self, hook_manager):
        """Test uninstallation fails when hooks_dir is None."""
        hook_manager.hooks_dir = None

        result = hook_manager.uninstall_hooks()

        assert not result

    def test_uninstall_hooks_non_roadmap_hook(self, hook_manager):
        """Test uninstallation skips non-roadmap hooks."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pathlib.Path.read_text", return_value="#!/bin/bash\n# Some other hook"
            ),
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            result = hook_manager.uninstall_hooks()

            assert result
            # Should NOT unlink non-roadmap hooks
            mock_unlink.assert_not_called()

    def test_uninstall_hooks_exception(self, hook_manager):
        """Test uninstallation fails gracefully on exception."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", side_effect=OSError("Read error")),
        ):
            result = hook_manager.uninstall_hooks()

            assert not result


class TestGitHookManagerStatus:
    """Test Git hook status checking."""

    def test_get_hooks_status_all_installed(self, hook_manager):
        """Test getting status when all hooks are installed."""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="#!/bin/bash\n# roadmap-hook"),
            patch("pathlib.Path.stat") as mock_stat,
        ):
            # Mock file permissions (executable)
            mock_stat.return_value = Mock(st_mode=0o755)

            status = hook_manager.get_hooks_status()

            assert len(status) == 4
            for hook_name in ["post-commit", "pre-push", "post-merge", "post-checkout"]:
                assert hook_name in status
                assert status[hook_name]["installed"]
                assert status[hook_name]["is_roadmap_hook"]
                assert status[hook_name]["executable"]
                assert status[hook_name]["file_exists"]

    def test_get_hooks_status_no_hooks_dir(self, hook_manager):
        """Test getting status when hooks_dir is None."""
        hook_manager.hooks_dir = None

        status = hook_manager.get_hooks_status()

        assert status == {}
