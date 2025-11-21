"""Integration tests for CLI commands.

Tests CLI commands end-to-end with proper database and file system isolation.
Uses Click's CliRunner for testing CLI interactions.
"""

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing."""
    return CliRunner()


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


@pytest.fixture
def isolated_roadmap_with_issues(isolated_roadmap):
    """Create an isolated roadmap with sample issues.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    cli_runner, temp_dir = isolated_roadmap

    # Create a few test issues
    issues = [
        {"title": "Fix bug in parser", "type": "bug", "priority": "high"},
        {"title": "Add new feature", "type": "feature", "priority": "medium"},
        {"title": "Update documentation", "type": "other", "priority": "low"},
    ]

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
        assert result.exit_code == 0, f"Issue creation failed: {result.output}"

    yield cli_runner, temp_dir


class TestCLIInit:
    """Test init command."""

    def test_init_non_interactive(self, cli_runner):
        """Test initializing roadmap non-interactively."""
        with cli_runner.isolated_filesystem():
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

            assert result.exit_code == 0
            assert ".roadmap" in os.listdir(".")
            assert (
                "initialized" in result.output.lower()
                or "success" in result.output.lower()
            )

    def test_init_with_description(self, cli_runner):
        """Test init with project description."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test",
                    "--description",
                    "Test project",
                    "--non-interactive",
                    "--skip-github",
                ],
            )

            assert result.exit_code == 0

    def test_init_creates_database(self, cli_runner):
        """Test that init creates the database file."""
        with cli_runner.isolated_filesystem():
            cli_runner.invoke(
                main,
                [
                    "init",
                    "--project-name",
                    "Test",
                    "--non-interactive",
                    "--skip-github",
                ],
            )

            roadmap_dir = Path(".roadmap")
            assert roadmap_dir.exists()
            # Database should be created (check for .db file or state directory)
            db_files = list(roadmap_dir.glob("*.db"))
            assert len(db_files) > 0 or (roadmap_dir / "state").exists()

    def test_init_help(self, cli_runner):
        """Test init help command."""
        result = cli_runner.invoke(main, ["init", "--help"])

        assert result.exit_code == 0
        assert "init" in result.output.lower()
        assert "project" in result.output.lower()


class TestCLIStatus:
    """Test status command."""

    def test_status_without_init(self, cli_runner):
        """Test status command before initialization."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["status"])

            # Should handle gracefully - either show not initialized or exit with error
            assert "not initialized" in result.output.lower() or result.exit_code != 0

    def test_status_after_init(self, isolated_roadmap):
        """Test status command after initialization."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        # Status should show roadmap status and issue/milestone info
        assert "roadmap" in result.output.lower() or "status" in result.output.lower()

    def test_status_help(self, cli_runner):
        """Test status help command."""
        result = cli_runner.invoke(main, ["status", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()


class TestCLIHealth:
    """Test health command."""

    def test_health_check(self, cli_runner):
        """Test health check command."""
        result = cli_runner.invoke(main, ["health"])

        assert result.exit_code == 0
        # Health should report status
        assert (
            "health" in result.output.lower()
            or "status" in result.output.lower()
            or "ok" in result.output.lower()
        )

    def test_health_help(self, cli_runner):
        """Test health help command."""
        result = cli_runner.invoke(main, ["health", "--help"])

        assert result.exit_code == 0


class TestCLIIssueCreate:
    """Test issue create command."""

    def test_create_issue_minimal(self, isolated_roadmap):
        """Test creating issue with minimal arguments."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["issue", "create", "Test Issue"],  # TITLE is positional
        )

        assert result.exit_code == 0
        assert "created" in result.output.lower() or "issue" in result.output.lower()

    def test_create_issue_with_all_fields(self, isolated_roadmap):
        """Test creating issue with all fields."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            [
                "issue",
                "create",
                "Feature Request",  # TITLE is positional
                "--type",
                "feature",
                "--priority",
                "high",
                "--estimate",
                "4.5",
            ],
        )

        assert result.exit_code == 0

    def test_create_issue_help(self, cli_runner):
        """Test issue create help."""
        result = cli_runner.invoke(main, ["issue", "create", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()
        assert "title" in result.output.lower()


class TestCLIIssueList:
    """Test issue list command."""

    def test_list_issues(self, isolated_roadmap_with_issues):
        """Test listing all issues."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list"])

        assert result.exit_code == 0
        # Should show the created issues
        assert "fix bug" in result.output.lower() or "parser" in result.output.lower()

    def test_list_issues_with_status_filter(self, isolated_roadmap_with_issues):
        """Test listing issues with status filter."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list", "--status", "todo"])

        assert result.exit_code == 0

    def test_list_issues_with_priority_filter(self, isolated_roadmap_with_issues):
        """Test listing issues with priority filter."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "list", "--priority", "high"])

        assert result.exit_code == 0

    def test_list_issues_empty(self, isolated_roadmap):
        """Test listing issues when none exist."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["issue", "list"])

        assert result.exit_code == 0
        # Should handle empty list gracefully
        assert (
            "no issues" in result.output.lower()
            or result.output.strip() == ""
            or "issue" in result.output.lower()
        )

    def test_list_issues_help(self, cli_runner):
        """Test issue list help."""
        result = cli_runner.invoke(main, ["issue", "list", "--help"])

        assert result.exit_code == 0


class TestCLIIssueUpdate:
    """Test issue update command."""

    def test_update_issue_title(self, isolated_roadmap_with_issues):
        """Test updating issue title."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        # Update using a known issue number (they're created sequentially)
        result = cli_runner.invoke(
            main,
            ["issue", "update", "1", "--title", "Updated Title"],
        )

        assert result.exit_code == 0 or "updated" in result.output.lower()

    def test_update_issue_priority(self, isolated_roadmap_with_issues):
        """Test updating issue priority."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["issue", "update", "1", "--priority", "critical"],
        )

        assert result.exit_code == 0

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

    def test_update_issue_help(self, cli_runner):
        """Test issue update help."""
        result = cli_runner.invoke(main, ["issue", "update", "--help"])

        assert result.exit_code == 0


class TestCLIIssueDelete:
    """Test issue delete command."""

    def test_delete_issue(self, isolated_roadmap_with_issues):
        """Test deleting an issue."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        # Delete issue #1 with confirmation
        result = cli_runner.invoke(
            main,
            ["issue", "delete", "1"],
            input="y\n",
        )

        assert result.exit_code == 0 or "deleted" in result.output.lower()

    def test_delete_issue_force(self, isolated_roadmap_with_issues):
        """Test force deleting an issue."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["issue", "delete", "2", "--yes"],  # --yes skips confirmation
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

    def test_delete_issue_help(self, cli_runner):
        """Test issue delete help."""
        result = cli_runner.invoke(main, ["issue", "delete", "--help"])

        assert result.exit_code == 0


class TestCLIIssueWorkflow:
    """Test issue workflow commands (start, finish, done, progress)."""

    def test_start_issue(self, isolated_roadmap_with_issues):
        """Test starting work on an issue."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "start", "1"])

        # Should succeed or show status change
        assert (
            result.exit_code == 0
            or "start" in result.output.lower()
            or "in_progress" in result.output.lower()
        )

    def test_finish_issue(self, isolated_roadmap_with_issues):
        """Test finishing an issue."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        # Start first
        cli_runner.invoke(main, ["issue", "start", "1"])

        # Then finish
        result = cli_runner.invoke(main, ["issue", "finish", "1"])

        assert (
            result.exit_code == 0
            or "finish" in result.output.lower()
            or "completed" in result.output.lower()
        )

    def test_done_issue(self, isolated_roadmap_with_issues):
        """Test marking issue as done."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "done", "1"])

        assert result.exit_code == 0 or "done" in result.output.lower()

    def test_update_progress(self, isolated_roadmap_with_issues):
        """Test updating issue progress."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["issue", "progress", "1", "50"])

        assert result.exit_code == 0 or "progress" in result.output.lower()

    def test_block_issue(self, isolated_roadmap_with_issues):
        """Test blocking an issue."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["issue", "block", "1", "--reason", "Waiting for dependency"],
        )

        assert result.exit_code == 0 or "block" in result.output.lower()

    def test_unblock_issue(self, isolated_roadmap_with_issues):
        """Test unblocking an issue."""
        cli_runner, temp_dir = isolated_roadmap_with_issues

        # Block first
        cli_runner.invoke(
            main,
            ["issue", "block", "1", "--reason", "Test"],
        )

        # Then unblock
        result = cli_runner.invoke(main, ["issue", "unblock", "1"])

        assert result.exit_code == 0 or "unblock" in result.output.lower()

    def test_start_issue_help(self, cli_runner):
        """Test start command help."""
        result = cli_runner.invoke(main, ["issue", "start", "--help"])

        assert result.exit_code == 0

    def test_finish_issue_help(self, cli_runner):
        """Test finish command help."""
        result = cli_runner.invoke(main, ["issue", "finish", "--help"])

        assert result.exit_code == 0


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

    def test_all_issue_subcommands_have_help(self, cli_runner):
        """Test that all issue subcommands have help."""
        subcommands = [
            "create",
            "list",
            "update",
            "delete",
            "start",
            "finish",
            "done",
            "progress",
            "block",
            "unblock",
            "deps",
        ]

        for cmd in subcommands:
            result = cli_runner.invoke(main, ["issue", cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} help failed"


class TestCLIRootHelp:
    """Test root CLI help."""

    def test_root_help(self, cli_runner):
        """Test root help command."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "roadmap" in result.output.lower()

    def test_no_command_shows_help(self, cli_runner):
        """Test that running without command shows help."""
        result = cli_runner.invoke(main, [])

        # Click may return exit code 0 (help) or 2 (missing command)
        assert result.exit_code in [0, 2]
        assert "roadmap" in result.output.lower() or "usage" in result.output.lower()

    def test_version_flag(self, cli_runner):
        """Test --version flag."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        # Should show version info
        assert "version" in result.output.lower() or len(result.output.strip()) > 0
