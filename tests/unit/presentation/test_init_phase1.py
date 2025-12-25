"""Tests for roadmap initialization commands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


class TestInitCommand:
    """Test roadmap init command."""

    def test_init_non_interactive_creates_directory(self, cli_runner):
        """Test that init with --non-interactive creates .roadmap directory."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main, ["init", "--non-interactive", "--skip-github", "--skip-project"]
            )
            assert result.exit_code == 0
            assert Path(".roadmap").exists()

    def test_init_force_reinit_removes_old_files(self, cli_runner):
        """Test that force reinit removes old configuration files."""
        with cli_runner.isolated_filesystem():
            # First init
            res1 = cli_runner.invoke(
                main, ["init", "--non-interactive", "--skip-github"]
            )
            assert res1.exit_code == 0
            assert Path(".roadmap").exists()

            # Add marker file
            (Path(".roadmap") / "marker.txt").write_text("old")
            assert (Path(".roadmap") / "marker.txt").exists()

            # Force reinit
            res2 = cli_runner.invoke(
                main, ["init", "--non-interactive", "--force", "--skip-github"]
            )
            assert res2.exit_code == 0
            # Marker should be gone after force reinit
            assert not (Path(".roadmap") / "marker.txt").exists()
