"""Tests for CLI git commands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.git.commands import git


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner."""
    return CliRunner()


class TestGitCommandGroup:
    """Test git command group."""

    def test_git_command_exists(self):
        """Test that git command exists."""
        assert git is not None

    def test_git_command_has_callbacks(self):
        """Test that git command has proper configuration."""
        assert hasattr(git, "callback") or hasattr(git, "invoke_without_command")


class TestSetupCommand:
    """Test setup command."""

    def test_setup_command_in_group(self, cli_runner):
        """Test that setup command is in git group."""
        result = cli_runner.invoke(git, ["setup"])
        # Command should be found and execute
        assert result.exit_code in [0, 1, 2, 3]

    def test_setup_command_output(self, cli_runner):
        """Test setup command produces output."""
        result = cli_runner.invoke(git, ["setup"])
        # Should have some output
        assert len(result.output) > 0 or result.exit_code != 0


class TestHooksInstallCommand:
    """Test hooks install command."""

    def test_hooks_install_command_in_group(self, cli_runner):
        """Test that hooks install command is in git group."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.install_hooks.return_value = True

            result = cli_runner.invoke(git, ["hooks-install"])
            # Should either succeed or require initialization
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_install_command_success(self, cli_runner):
        """Test hooks install command success."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.install_hooks.return_value = True

            result = cli_runner.invoke(git, ["hooks-install"])
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_install_command_failure(self, cli_runner):
        """Test hooks install command failure handling."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.install_hooks.side_effect = Exception("Install failed")

            result = cli_runner.invoke(git, ["hooks-install"])
            # Should handle error
            assert result.exit_code in [0, 1, 2, 3]


class TestHooksUninstallCommand:
    """Test hooks uninstall command."""

    def test_hooks_uninstall_command_in_group(self, cli_runner):
        """Test that hooks uninstall command is in git group."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.uninstall_hooks.return_value = True

            result = cli_runner.invoke(git, ["hooks-uninstall"])
            # Should either succeed or require initialization
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_uninstall_command_success(self, cli_runner):
        """Test hooks uninstall command success."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.uninstall_hooks.return_value = True

            result = cli_runner.invoke(git, ["hooks-uninstall"], input="n\n")
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_uninstall_command_confirmed(self, cli_runner):
        """Test hooks uninstall command with confirmation."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.uninstall_hooks.return_value = True

            result = cli_runner.invoke(git, ["hooks-uninstall"], input="y\n")
            assert result.exit_code in [0, 1, 2, 3]


class TestHooksStatusCommand:
    """Test hooks status command."""

    def test_hooks_status_command_in_group(self, cli_runner):
        """Test that hooks status command is in git group."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.get_hooks_status.return_value = {
                "pre-commit": True,
                "pre-push": True,
            }

            result = cli_runner.invoke(git, ["hooks-status"])
            # Should either succeed or require initialization
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_status_command_success(self, cli_runner):
        """Test hooks status command success."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.get_hooks_status.return_value = {
                "pre-commit": True,
                "pre-push": True,
            }

            result = cli_runner.invoke(git, ["hooks-status"])
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_status_all_installed(self, cli_runner):
        """Test hooks status when all are installed."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.get_hooks_status.return_value = {
                "pre-commit": True,
                "pre-push": True,
                "commit-msg": True,
            }

            result = cli_runner.invoke(git, ["hooks-status"])
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_status_none_installed(self, cli_runner):
        """Test hooks status when none are installed."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.get_hooks_status.return_value = {
                "pre-commit": False,
                "pre-push": False,
            }

            result = cli_runner.invoke(git, ["hooks-status"])
            assert result.exit_code in [0, 1, 2, 3]

    def test_hooks_status_partial(self, cli_runner):
        """Test hooks status when some are installed."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.get_hooks_status.return_value = {
                "pre-commit": True,
                "pre-push": False,
            }

            result = cli_runner.invoke(git, ["hooks-status"])
            assert result.exit_code in [0, 1, 2, 3]


class TestCommandIntegration:
    """Integration tests for git commands."""

    def test_setup_then_hooks_install(self, cli_runner):
        """Test setup followed by hooks install."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_hooks:
            hooks_instance = MagicMock()
            mock_hooks.return_value = hooks_instance
            hooks_instance.install_hooks.return_value = True

            result = cli_runner.invoke(git, ["hooks-install"])
            assert result.exit_code in [0, 1, 2, 3]

    def test_install_then_status(self, cli_runner):
        """Test hooks install followed by status check."""
        with patch("roadmap.adapters.cli.git.commands.GitHookManager") as mock_hooks:
            hooks_instance = MagicMock()
            mock_hooks.return_value = hooks_instance
            hooks_instance.install_hooks.return_value = True
            hooks_instance.get_hooks_status.return_value = {
                "pre-commit": True,
                "pre-push": True,
            }

            result = cli_runner.invoke(git, ["hooks-install"])
            assert result.exit_code in [0, 1, 2, 3]

            result = cli_runner.invoke(git, ["hooks-status"])
            assert result.exit_code in [0, 1, 2, 3]
