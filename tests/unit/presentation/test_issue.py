"""Tests for issue-related CLI commands."""

import pytest
from roadmap.adapters.cli import main


class TestIssueCommands:
    """Test issue CLI commands."""

    def test_issue_help(self, cli_runner):
        """Test issue command help."""
        result = cli_runner.invoke(main, ["issue", "--help"])
        assert result.exit_code == 0
        assert "Manage issues" in result.output

    @pytest.mark.parametrize("initialized,should_succeed", [
        (True, True),
        (False, False),
    ])
    def test_issue_create_variants(self, cli_runner, initialized, should_succeed):
        """Test creating an issue with and without initialized roadmap."""
        with cli_runner.isolated_filesystem():
            if initialized:
                init_result = cli_runner.invoke(
                    main, ["init", "-y", "--skip-github", "--skip-project"]
                )
                assert init_result.exit_code == 0

            result = cli_runner.invoke(main, ["issue", "create", "test-issue"])
            
            if should_succeed:
                assert result.exit_code == 0
            else:
                assert result.exit_code != 0
                assert "Roadmap not initialized" in result.output

    @pytest.mark.parametrize("initialized,should_succeed", [
        (True, True),
        (False, False),
    ])
    def test_issue_list_variants(self, cli_runner, initialized, should_succeed):
        """Test listing issues with and without initialized roadmap."""
        with cli_runner.isolated_filesystem():
            if initialized:
                init_result = cli_runner.invoke(
                    main, ["init", "-y", "--skip-github", "--skip-project"]
                )
                assert init_result.exit_code == 0

            result = cli_runner.invoke(main, ["issue", "list"])
            
            if should_succeed:
                assert result.exit_code == 0
            else:
                assert result.exit_code != 0
                assert "❌ Roadmap not initialized" in result.output
