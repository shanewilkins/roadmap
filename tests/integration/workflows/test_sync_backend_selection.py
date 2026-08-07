"""Integration tests for sync backend selection during initialization.

Tests that verify the sync_backend option is properly handled during init,
stored in config, and can be used for sync operations.
"""

from pathlib import Path
from typing import Any

import yaml

from roadmap.adapters.cli import main


class TestSyncBackendSelection:
    """Test sync backend selection during initialization."""

    def test_init_github_backend_default(self, cli_runner):
        """Test that github is the default sync backend."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--name",
                    "test_roadmap",
                    "--project-name",
                    "Test",
                    "--yes",
                ],
            )

            assert result.exit_code == 0

            # Check config has github backend set
            config_path = Path("test_roadmap/config.yaml")
            assert config_path.exists()
            with open(config_path) as f:
                config: Any = yaml.safe_load(f)
                assert isinstance(config, dict)
                assert config.get("github", {}).get("sync_backend") == "github"

    def test_init_git_backend_selection(self, cli_runner):
        """Test that git sync backend can be selected during init."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--name",
                    "test_roadmap_git",
                    "--project-name",
                    "Test",
                    "--sync-backend",
                    "git",
                    "--skip-github",
                    "--yes",
                ],
            )

            assert result.exit_code == 0

            # Check config has git backend set
            config_path = Path("test_roadmap_git/config.yaml")
            assert config_path.exists()
            with open(config_path) as f:
                config: Any = yaml.safe_load(f)
                assert isinstance(config, dict)
                # Should have sync_backend in github section
                backend = config.get("github", {}).get("sync_backend")
                assert backend == "git", f"Expected 'git' but got {backend}"

    def test_init_invalid_backend_rejected(self, cli_runner):
        """Test that invalid sync backend values are rejected."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--name",
                    "test_roadmap",
                    "--project-name",
                    "Test",
                    "--sync-backend",
                    "invalid",
                    "--yes",
                ],
            )

            assert result.exit_code != 0
            assert (
                "Invalid sync_backend" in result.output
                or "invalid" in result.output.lower()
            )

    def test_init_skip_github_with_git_backend(self, cli_runner):
        """Test init with git backend and no GitHub integration."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--name",
                    "test_roadmap_self_hosted",
                    "--project-name",
                    "Self Hosted",
                    "--sync-backend",
                    "git",
                    "--skip-github",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert (
                "Roadmap initialized" in result.output
                or "successfully" in result.output.lower()
            )

            # Verify project was created
            expected_projects_dir = Path("test_roadmap_self_hosted/projects")
            assert expected_projects_dir.exists()
