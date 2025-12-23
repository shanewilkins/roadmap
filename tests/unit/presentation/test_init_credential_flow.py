"""Tests for credential flow in initialization."""

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click test runner."""
    return CliRunner()


class TestInitCredentialFlow:
    """Test credential flow in init command."""

    def test_init_with_skip_github_flag(self, cli_runner):
        """Test that init succeeds when --skip-github flag is set."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "-y",
                    "--skip-github",
                    "--skip-project",
                ],
            )
            # Should succeed without errors
            assert result.exit_code == 0

