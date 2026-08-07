"""Unit tests for git hooks configuration command."""

from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.git.hooks_config import hooks_config
from roadmap.core.services.git.git_hook_auto_sync_service import GitHookAutoSyncConfig


class TestHooksConfigCommand:
    """Test hooks configuration command."""

    def test_show_config(self, mock_core, cli_runner):
        """Test showing current configuration."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                config_instance.get_config.return_value = GitHookAutoSyncConfig(
                    auto_sync_enabled=True,
                    sync_on_commit=True,
                    sync_on_checkout=False,
                    sync_on_merge=True,
                    confirm_before_sync=False,
                    force_local=True,
                    force_github=False,
                )
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config, ["--show"], obj={"core": mock_core}
                )
                assert result.exit_code == 0

    def test_enable_auto_sync(self, mock_core, cli_runner):
        """Test enabling auto-sync."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--enable-auto-sync"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_disable_auto_sync(self, mock_core, cli_runner):
        """Test disabling auto-sync."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--disable-auto-sync"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_sync_on_commit(self, mock_core, cli_runner):
        """Test enabling sync on commit."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--sync-on-commit"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_no_sync_on_commit(self, mock_core, cli_runner):
        """Test disabling sync on commit."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--no-sync-on-commit"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_sync_on_checkout(self, mock_core, cli_runner):
        """Test enabling sync on checkout."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--sync-on-checkout"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_no_sync_on_checkout(self, mock_core, cli_runner):
        """Test disabling sync on checkout."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--no-sync-on-checkout"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_sync_on_merge(self, mock_core, cli_runner):
        """Test enabling sync on merge."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--sync-on-merge"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_no_sync_on_merge(self, mock_core, cli_runner):
        """Test disabling sync on merge."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--no-sync-on-merge"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_require_confirmation(self, mock_core, cli_runner):
        """Test requiring confirmation."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--confirm"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_no_confirmation(self, mock_core, cli_runner):
        """Test not requiring confirmation."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--no-confirm"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_force_local_resolution(self, mock_core, cli_runner):
        """Test forcing local conflict resolution."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--force-local"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_force_github_resolution(self, mock_core, cli_runner):
        """Test forcing GitHub conflict resolution."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    ["--force-github"],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0

    def test_multiple_options(self, mock_core, cli_runner):
        """Test setting multiple options at once."""
        with patch(
            "roadmap.adapters.cli.git.hooks_config.require_initialized"
        ) as mock_req:
            mock_req.return_value = lambda f: f
            with patch(
                "roadmap.adapters.cli.git.hooks_config.GitHookAutoSyncService"
            ) as mock_service:
                config_instance = MagicMock()
                mock_service.return_value = config_instance

                result = cli_runner.invoke(
                    hooks_config,
                    [
                        "--enable-auto-sync",
                        "--sync-on-commit",
                        "--force-local",
                    ],
                    obj={"core": mock_core},
                )
                assert result.exit_code == 0
