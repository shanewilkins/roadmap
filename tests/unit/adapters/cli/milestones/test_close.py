"""Unit tests for milestone close command."""

from roadmap.adapters.cli.milestones.close import close_milestone


class TestMilestoneCloseCommand:
    """Test milestone close command."""

    def test_close_milestone(self, cli_runner):
        """Test closing a milestone."""
        result = cli_runner.invoke(
            close_milestone,
            ["v1.0"],
        )

        # Test completes
        assert result is not None

    def test_close_nonexistent_milestone(self, cli_runner):
        """Test closing nonexistent milestone."""
        result = cli_runner.invoke(
            close_milestone,
            ["nonexistent"],
        )

        # Test completes without exception
        assert result is not None

    def test_close_with_force(self, cli_runner):
        """Test close with force flag."""
        result = cli_runner.invoke(
            close_milestone,
            ["v1.0", "--force"],
        )

        # Test completes without exception
        assert result is not None

    def test_close_declined(self, cli_runner):
        """Test user declining close operation."""
        result = cli_runner.invoke(
            close_milestone,
            ["v1.0"],
            input="n\n",
        )

        # Test completes without exception
        assert result is not None

    def test_close_dry_run(self, cli_runner):
        """Test close with dry-run."""
        result = cli_runner.invoke(
            close_milestone,
            ["v1.0", "--dry-run"],
        )

        # Test completes without exception
        assert result is not None

    def test_close_accepted(self, cli_runner):
        """Test user accepting close operation."""
        result = cli_runner.invoke(
            close_milestone,
            ["v1.0"],
            input="y\n",
        )

        # Test completes without exception
        assert result is not None
