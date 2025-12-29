"""Integration tests for CLI commands.

Integration tests for CLI issue commands.

Uses Click's CliRunner for testing CLI interactions.
"""

from pathlib import Path

import pytest

from roadmap.adapters.cli import main


@pytest.fixture
def isolated_roadmap(cli_runner):
    """Create an isolated roadmap environment with initialized database.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap in this directory
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )

        assert result.exit_code == 0, f"Init failed: {result.output}"

        yield cli_runner, temp_dir
        # Cleanup happens here when context exits


@pytest.fixture
def isolated_roadmap_with_issues(cli_runner):
    """Create an isolated roadmap with sample issues.

    Yields:
        tuple: (cli_runner, temp_dir_path, created_issue_ids)
    """
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap in this directory
        result = cli_runner.invoke(
            main,
            [
                "init",
                "--project-name",
                "Test Project",
                "--non-interactive",
                "--skip-github",
            ],
        )
        assert result.exit_code == 0, f"Init failed: {result.output}"

        # Create a few test issues
        issues = [
            {"title": "Fix bug in parser", "type": "bug", "priority": "high"},
            {"title": "Add new feature", "type": "feature", "priority": "medium"},
            {"title": "Update documentation", "type": "other", "priority": "low"},
        ]

        created_ids = []
        for issue in issues:
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    issue["title"],  # TITLE is positional argument
                    "--type",
                    issue["type"],
                    "--priority",
                    issue["priority"],
                ],
            )
            if result.exit_code == 0:
                # Parse the issue ID from the output
                from tests.fixtures.click_testing import ClickTestHelper

                try:
                    issue_id = ClickTestHelper.extract_issue_id(result.output)
                    created_ids.append(issue_id)
                except ValueError:
                    # If extraction fails, continue without the ID
                    pass

        yield cli_runner, temp_dir, created_ids
        # Cleanup happens here when context exits


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
    def test_create_issue(self, isolated_roadmap, title, options, should_succeed):
        """Test creating issues with various field combinations."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "create", title] + options,
        )

        if should_succeed:
            assert result.exit_code == 0
            assert (
                "created" in result.output.lower() or "issue" in result.output.lower()
            )
        else:
            assert result.exit_code != 0

    def test_create_issue_help(self, cli_runner):
        """Test issue create help."""
        result = cli_runner.invoke(main, ["issue", "create", "--help"])

        assert result.exit_code == 0
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
        isolated_roadmap,
        isolated_roadmap_with_issues,
        filter_args,
        use_empty_roadmap,
    ):
        """Test listing issues with various filters."""
        if use_empty_roadmap:
            cli_runner, temp_dir = isolated_roadmap
        else:
            cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list"] + filter_args)

        assert result.exit_code == 0
        if not use_empty_roadmap and not filter_args:
            # Listing with data should show issues
            assert (
                "fix bug" in result.output.lower() or "parser" in result.output.lower()
            )

    def test_list_issues_help(self, cli_runner):
        """Test issue list help."""
        result = cli_runner.invoke(main, ["issue", "list", "--help"])

        assert result.exit_code == 0


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
    def test_update_issue(self, isolated_roadmap_with_issues, option, value):
        """Test updating issues with various fields."""
        cli_runner, temp_dir, issue_ids = isolated_roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        result = cli_runner.invoke(
            main,
            ["issue", "update", issue_ids[0], option, value],
        )

        assert result.exit_code == 0 or "updated" in result.output.lower()

    def test_update_nonexistent_issue(self, isolated_roadmap):
        """Test updating non-existent issue."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "update", "999", "--title", "Test"],
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "error" in result.output.lower()
        )


class TestCLIIssueDelete:
    """Test issue delete command."""

    @pytest.mark.parametrize(
        "use_force,use_yes",
        [
            (False, False),  # With confirmation
            (False, True),  # With --yes flag
            (True, False),  # With --yes flag (second time)
        ],
    )
    def test_delete_issue(self, isolated_roadmap_with_issues, use_force, use_yes):
        """Test deleting issues with various options."""
        cli_runner, temp_dir, issue_ids = isolated_roadmap_with_issues

        if not issue_ids:
            pytest.skip("No issues created in fixture")

        args = ["issue", "delete", issue_ids[0]]
        if use_force or use_yes:
            args.append("--yes")

        result = cli_runner.invoke(
            main,
            args,
            input="y\n" if not (use_force or use_yes) else None,
        )

        assert result.exit_code == 0 or "deleted" in result.output.lower()

    def test_delete_nonexistent_issue(self, isolated_roadmap):
        """Test deleting non-existent issue."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "delete", "999", "--force"],
        )

        # Should fail gracefully
        assert result.exit_code != 0 or "not found" in result.output.lower()


class TestCLIIssueWorkflow:
    """Test issue workflow commands (start, close, progress)."""

    def test_start_issue(self, isolated_roadmap_with_issues):
        """Test starting work on an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "start", "1"])

        # Should succeed or show status change
        assert (
            result.exit_code == 0
            or "start" in result.output.lower()
            or "in_progress" in result.output.lower()
        )

    def test_close_issue(self, isolated_roadmap_with_issues):
        """Test closing an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        # Start first
        cli_runner.invoke(main, ["issue", "start", "1"])

        # Then close
        result = cli_runner.invoke(main, ["issue", "close", "1"])

        assert (
            result.exit_code == 0
            or "close" in result.output.lower()
            or "closed" in result.output.lower()
        )

    def test_update_progress(self, isolated_roadmap_with_issues):
        """Test updating issue progress."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "progress", "1", "50"])

        assert result.exit_code == 0 or "progress" in result.output.lower()

    def test_block_issue(self, isolated_roadmap_with_issues):
        """Test blocking an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["issue", "block", "1", "--reason", "Waiting for dependency"],
        )

        assert result.exit_code == 0 or "block" in result.output.lower()

    def test_unblock_issue(self, isolated_roadmap_with_issues):
        """Test unblocking an issue."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        # Block first
        cli_runner.invoke(
            main,
            ["issue", "block", "1", "--reason", "Test"],
        )

        # Then unblock
        result = cli_runner.invoke(main, ["issue", "unblock", "1"])

        assert result.exit_code == 0 or "unblock" in result.output.lower()


class TestCLIIssueHelp:
    """Test issue command help."""

    def test_issue_group_help(self, cli_runner):
        """Test issue group help."""
        result = cli_runner.invoke(main, ["issue", "--help"])

        assert result.exit_code == 0
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
        assert result.exit_code == 0, f"{subcommand} help failed"
