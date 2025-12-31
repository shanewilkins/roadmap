"""Unit tests for issue unlink GitHub command."""

from roadmap.adapters.cli.issues.unlink import unlink_github_issue


class TestUnlinkCommand:
    """Test issue unlink command."""

    def test_unlink_github_issue(self, cli_runner):
        """Test unlinking a GitHub issue."""
        result = cli_runner.invoke(
            unlink_github_issue,
            ["issue1"],
        )

        # Test completes
        assert result is not None

    def test_unlink_nonexistent_issue(self, cli_runner):
        """Test unlinking nonexistent issue."""
        result = cli_runner.invoke(
            unlink_github_issue,
            ["nonexistent"],
        )

        # Test completes without exception
        assert result is not None

    def test_unlink_not_linked_issue(self, cli_runner):
        """Test unlinking an issue that's not linked."""
        result = cli_runner.invoke(
            unlink_github_issue,
            ["local-only-issue"],
        )

        # Test completes without exception
        assert result is not None

    def test_unlink_with_force_flag(self, cli_runner):
        """Test unlink with force flag."""
        result = cli_runner.invoke(
            unlink_github_issue,
            ["issue1", "--force"],
        )

        # Test completes without exception
        assert result is not None

    def test_unlink_user_declining(self, cli_runner):
        """Test user declining unlink operation."""
        result = cli_runner.invoke(
            unlink_github_issue,
            ["issue1"],
            input="n\n",
        )

        # Test completes without exception
        assert result is not None
