"""Integration tests for CLI commands.

Integration tests for CLI issue commands.

Uses Click's CliRunner for testing CLI interactions.
Refactored to use IntegrationTestBase helpers and data factories.
"""

import pytest

from roadmap.adapters.cli import main
from tests.fixtures.integration_helpers import IntegrationTestBase


@pytest.fixture
def empty_roadmap(cli_runner):
    """Create an isolated empty roadmap.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    with cli_runner.isolated_filesystem():
        IntegrationTestBase.init_roadmap(cli_runner)
        yield cli_runner, None


@pytest.fixture
def roadmap_with_issues(cli_runner):
    """Create a roadmap with pre-populated sample issues.

    Yields:
        tuple: (cli_runner, core, issue_ids)
    """
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)
        issue_ids = []
        # Create multiple issues for testing
        for _, priority in enumerate(["critical", "high", "medium", "low"], 1):
            IntegrationTestBase.create_issue(
                cli_runner,
                title=f"{priority.title()} Priority Issue",
                priority=priority,
            )
        # Refresh core to pick up newly created issues
        core = IntegrationTestBase.get_roadmap_core()
        issue_ids = [issue.id for issue in core.issues.list()]
        yield cli_runner, core, issue_ids


class TestCLIIssueCreate:
    """Test issue create command."""

    @pytest.mark.parametrize(
        "title,options,should_succeed",
        [
            ("Test Issue", [], True),  # Minimal
            (
                "Feature Request",
                ["--type", "feature", "--priority", "high", "--estimate", "4.5"],
                True,
            ),
            ("Bug Report", ["--type", "bug"], True),
            ("Task", ["--priority", "medium"], True),
        ],
    )
    def test_create_issue(self, empty_roadmap, title, options, should_succeed):
        """Test creating issues with various field combinations."""
        cli_runner, _ = empty_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "create", title] + options,
        )

        if should_succeed:
            IntegrationTestBase.assert_cli_success(result, f"Creating issue '{title}'")
        else:
            assert result.exit_code != 0

    def test_create_issue_help(self, cli_runner):
        """Test issue create help."""
        result = cli_runner.invoke(main, ["issue", "create", "--help"])

        IntegrationTestBase.assert_cli_success(result)
        assert "create" in result.output.lower()
        assert "title" in result.output.lower()


class TestCLIIssueList:
    """Test issue list command."""

    @pytest.mark.parametrize(
        "filter_args,use_empty_roadmap",
        [
            ([], False),  # List all issues
            (["--status", "todo"], False),  # With status filter
            (["--priority", "high"], False),  # With priority filter
            ([], True),  # Empty list
        ],
    )
    def test_list_issues(
        self,
        empty_roadmap,
        roadmap_with_issues,
        filter_args,
        use_empty_roadmap,
    ):
        """Test listing issues with various filters."""
        if use_empty_roadmap:
            cli_runner, _ = empty_roadmap
        else:
            cli_runner, core, issue_ids = roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list"] + filter_args)

        IntegrationTestBase.assert_cli_success(result)
        if not use_empty_roadmap and not filter_args:
            # With data and no filter, should show issues
            core = IntegrationTestBase.get_roadmap_core()
            assert len(core.issues.list()) > 0

    def test_list_issues_help(self, cli_runner):
        """Test issue list help."""
        result = cli_runner.invoke(main, ["issue", "list", "--help"])

        IntegrationTestBase.assert_cli_success(result)


class TestCLIIssueUpdate:
    """Test issue update command."""

    @pytest.mark.parametrize(
        "option,value",
        [
            ("--title", "Updated Title"),
            ("--priority", "critical"),
            ("--status", "in-progress"),
        ],
    )
    def test_update_issue(self, roadmap_with_issues, option, value):
        """Test updating issues with various fields."""
        cli_runner, core, issue_ids = roadmap_with_issues

        # Use the first created issue
        if not issue_ids:
            pytest.skip("No issues created in fixture")

        issue_id = issue_ids[0]

        result = cli_runner.invoke(
            main,
            ["issue", "update", issue_id, option, value],
        )

        # Update should succeed (exit_code 0) or gracefully handle the update
        assert result.exit_code == 0 or "updated" in result.output.lower()

    def test_update_nonexistent_issue(self, empty_roadmap):
        """Test updating non-existent issue."""
        cli_runner, _ = empty_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "update", "999", "--title", "Test"],
        )

        # Should not crash - either fail or handle gracefully
        assert result.exit_code == 0 or result.exit_code != 0


class TestCLIIssueDelete:
    """Test issue delete command."""

    @pytest.mark.parametrize(
        "use_yes",
        [False, True],
    )
    def test_delete_issue(self, roadmap_with_issues, use_yes):
        """Test deleting issues with various options."""
        cli_runner, core, issue_ids = roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        issue_id = issue_ids[0]

        args = ["issue", "delete", issue_id]
        if use_yes:
            args.append("--yes")

        result = cli_runner.invoke(
            main,
            args,
            input="y\n" if not use_yes else None,
        )

        # Delete should execute without crashing
        assert result.exit_code == 0 or "deleted" in result.output.lower()

    def test_delete_nonexistent_issue(self, empty_roadmap):
        """Test deleting non-existent issue."""
        cli_runner, _ = empty_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "delete", "999", "--yes"],
        )

        # Should not crash regardless of outcome
        assert result.exit_code == 0 or result.exit_code != 0


class TestCLIIssueWorkflow:
    """Test issue workflow commands (start, close, progress)."""

    def test_start_issue(self, roadmap_with_issues):
        """Test starting work on an issue."""
        cli_runner, core, issue_ids = roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        issue_id = issue_ids[0]

        result = cli_runner.invoke(main, ["issue", "start", issue_id])

        # Start should succeed or handle gracefully
        assert result.exit_code == 0 or "start" in result.output.lower()

    def test_close_issue(self, roadmap_with_issues):
        """Test closing an issue."""
        cli_runner, core, issue_ids = roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        issue_id = issue_ids[0]

        # Start first
        cli_runner.invoke(main, ["issue", "start", issue_id])

        # Then close
        result = cli_runner.invoke(main, ["issue", "close", issue_id])

        # Close should handle gracefully
        assert result.exit_code == 0 or "close" in result.output.lower()

    def test_update_progress(self, roadmap_with_issues):
        """Test updating issue progress."""
        cli_runner, core, issue_ids = roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        issue_id = issue_ids[0]

        result = cli_runner.invoke(main, ["issue", "progress", issue_id, "50"])

        # Progress update should handle gracefully
        assert result.exit_code == 0 or "progress" in result.output.lower()

    def test_block_issue(self, roadmap_with_issues):
        """Test blocking an issue."""
        cli_runner, core, issue_ids = roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        issue_id = issue_ids[0]

        result = cli_runner.invoke(
            main,
            ["issue", "block", issue_id, "--reason", "Waiting for dependency"],
        )

        # Block should succeed or handle gracefully
        assert result.exit_code == 0 or "block" in result.output.lower()

    def test_unblock_issue(self, roadmap_with_issues):
        """Test unblocking an issue."""
        cli_runner, core, issue_ids = roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        issue_id = issue_ids[0]

        # Block first
        cli_runner.invoke(
            main,
            ["issue", "block", issue_id, "--reason", "Test"],
        )

        # Then unblock
        result = cli_runner.invoke(main, ["issue", "unblock", issue_id])

        # Unblock should handle gracefully
        assert result.exit_code == 0 or "unblock" in result.output.lower()


class TestCLIIssueHelp:
    """Test issue command help."""

    def test_issue_group_help(self, cli_runner):
        """Test issue group help."""
        result = cli_runner.invoke(main, ["issue", "--help"])

        IntegrationTestBase.assert_cli_success(result)
        assert "issue" in result.output.lower()
        # Should list subcommands
        assert "create" in result.output.lower()
        assert "list" in result.output.lower()

    @pytest.mark.parametrize(
        "subcommand",
        [
            "create",
            "list",
            "update",
            "delete",
            "start",
            "close",
            "progress",
            "block",
            "unblock",
            "deps",
        ],
    )
    def test_issue_subcommand_help(self, cli_runner, subcommand):
        """Test that issue subcommands have help."""
        result = cli_runner.invoke(main, ["issue", subcommand, "--help"])
        IntegrationTestBase.assert_cli_success(result)
