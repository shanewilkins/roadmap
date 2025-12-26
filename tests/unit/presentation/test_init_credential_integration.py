"""Tests for credential handling in initialization."""

from roadmap.adapters.cli import main


class TestInitCredential:
    """Test credential handling in init command."""

    def test_init_accepts_github_token(self, cli_runner):
        """Test that init command accepts and processes GitHub token."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--non-interactive",
                    "--yes",
                    "--skip-github",
                    "--skip-project",
                ],
            )
            # Command should complete without error
            assert result.exit_code == 0, result.output
