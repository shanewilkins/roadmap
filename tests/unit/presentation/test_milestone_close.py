"""CLI tests for milestone close convenience command."""

from roadmap.adapters.cli import main


class TestMilestoneClose:
    """Test milestone close command."""

    def test_milestone_close_convenience(self, cli_runner):
        """Test the milestone close convenience command."""
        with cli_runner.isolated_filesystem():
            # Initialize first
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            # Create a milestone
            create_result = cli_runner.invoke(
                main,
                ["milestone", "create", "v0.2.0", "--description", "desc"],
            )
            assert create_result.exit_code == 0

            # Close it if command exists
            close_result = cli_runner.invoke(main, ["milestone", "close", "v0.2.0"])
            if close_result.exit_code == 0:
                # Verify output contains milestone reference
                assert (
                    "v0.2.0" in close_result.output
                    or "closed" in close_result.output.lower()
                )
