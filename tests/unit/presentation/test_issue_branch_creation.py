"""Tests for issue creation with Git branch creation."""

from roadmap.adapters.cli import main


class TestIssueBranchCreation:
    """Test issue creation with Git branch options."""

    def test_create_issue_with_git_branch_flag(self, cli_runner):
        """Test creating an issue with --git-branch flag."""
        with cli_runner.isolated_filesystem():
            # Initialize roadmap first
            init_result = cli_runner.invoke(
                main, ["init", "-y", "--skip-github", "--skip-project"]
            )
            assert init_result.exit_code == 0

            # Create issue with git branch flag
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    "--title",
                    "Test branch creation",
                    "--git-branch",
                    "--no-checkout",
                ],
            )
            # CLI should exit gracefully even if git isn't present
            assert result.exit_code == 0
