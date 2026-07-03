"""Unit tests for Git handler classes."""

from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.cli.git.handlers.git_connectivity_handler import (
    GitConnectivityHandler,
)
from roadmap.adapters.cli.git.handlers.git_hooks_handler import GitHooksHandler


class TestGitConnectivityHandler:
    """Focused tests for connectivity behavior and messaging."""

    @pytest.mark.parametrize(
        "success,message,expected_fragment",
        [
            (True, "Connected", "ready for syncing"),
            (False, "Failed", "Could not verify git remote access"),
        ],
    )
    def test_test_git_connectivity_handles_backend_result(
        self, success, message, expected_fragment
    ):
        """Connectivity path should print clear success/failure guidance."""
        console = Mock()
        handler = GitConnectivityHandler(console)
        core = Mock()

        with (
            patch(
                "roadmap.adapters.cli.services.sync_service.get_sync_backend",
                return_value=object(),
            ),
            patch(
                "roadmap.adapters.cli.services.sync_service.test_backend_connectivity",
                return_value=(success, message),
            ),
        ):
            handler.test_git_connectivity(core)

        printed = "\n".join(str(call) for call in console.print.call_args_list)
        assert expected_fragment in printed

    def test_test_git_connectivity_handles_missing_backend(self):
        """When backend init fails, user should get actionable message."""
        console = Mock()
        handler = GitConnectivityHandler(console)

        with patch(
            "roadmap.adapters.cli.services.sync_service.get_sync_backend",
            return_value=None,
        ):
            handler.test_git_connectivity(Mock())

        printed = "\n".join(str(call) for call in console.print.call_args_list)
        assert "Could not initialize Git backend" in printed

    def test_test_git_connectivity_handles_value_error(self):
        """ValueError path should explain repository precondition."""
        console = Mock()
        handler = GitConnectivityHandler(console)

        with patch(
            "roadmap.adapters.cli.services.sync_service.get_sync_backend",
            side_effect=ValueError("not a git repo"),
        ):
            handler.test_git_connectivity(Mock())

        printed = "\n".join(str(call) for call in console.print.call_args_list)
        assert "Git repository error" in printed
        assert "Make sure you're in a git repository" in printed


class TestGitHooksHandler:
    """Tests for hook management flows."""

    def test_install_hooks_success_and_failure_messages(self):
        """install_hooks should report both success and failure clearly."""
        console = Mock()
        handler = GitHooksHandler(console)

        with patch(
            "roadmap.adapters.cli.git.handlers.git_hooks_handler.GitHookManager"
        ) as manager_cls:
            manager = manager_cls.return_value
            manager.install_hooks.return_value = True
            handler.install_hooks(Mock())

            manager.install_hooks.return_value = False
            handler.install_hooks(Mock())

        printed = "\n".join(str(call) for call in console.print.call_args_list)
        assert "Git hooks installed successfully" in printed
        assert "Failed to install hooks" in printed

    def test_uninstall_hooks_success_message(self):
        """uninstall_hooks should surface success to user."""
        console = Mock()
        handler = GitHooksHandler(console)

        with patch(
            "roadmap.adapters.cli.git.handlers.git_hooks_handler.GitHookManager"
        ) as manager_cls:
            manager_cls.return_value.uninstall_hooks.return_value = True
            handler.uninstall_hooks(Mock())

        printed = "\n".join(str(call) for call in console.print.call_args_list)
        assert "Git hooks removed successfully" in printed

    def test_show_hooks_status_lists_hook_rows(self):
        """show_hooks_status should render row per hook with executability."""
        console = Mock()
        handler = GitHooksHandler(console)

        status = {
            "pre-commit": {"is_roadmap_hook": True, "executable": True},
            "post-commit": {"is_roadmap_hook": False, "executable": False},
        }

        with patch(
            "roadmap.adapters.cli.git.handlers.git_hooks_handler.GitHookManager"
        ) as manager_cls:
            manager_cls.return_value.get_hooks_status.return_value = status
            handler.show_hooks_status(Mock())

        printed = "\n".join(str(call) for call in console.print.call_args_list)
        assert "Git Hooks Status" in printed
        assert "pre-commit" in printed
        assert "post-commit" in printed
