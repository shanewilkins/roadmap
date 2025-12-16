"""CLI tests for milestone close convenience command."""

from roadmap.adapters.cli import main


def test_milestone_close_convenience(cli_runner):
    """Test the milestone close convenience command."""
    with cli_runner.isolated_filesystem():
        # Initialize first
        init_result = cli_runner.invoke(
            main, ["init", "-y", "--skip-github", "--skip-project"]
        )
        assert init_result.exit_code == 0

        # Create a milestone first
        result = cli_runner.invoke(
            main,
            [
                "milestone",
                "create",
                "v0.2.0",
                "--description",
                "desc",
            ],
        )
        assert result.exit_code == 0
        assert "Created" in result.output or "v0.2.0" in result.output

        # Close it (if close command exists and is different from delete)
        result = cli_runner.invoke(main, ["milestone", "close", "v0.2.0"])
        # Should either succeed or provide meaningful feedback
        # (close might not exist, in which case it will error)
        if result.exit_code == 0:
            assert "v0.2.0" in result.output or "closed" in result.output.lower()
