"""Tests for credential flow in initialization."""

from roadmap.adapters.cli import main


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
