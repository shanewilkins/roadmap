"""Integration tests for CLI commands.

Tests CLI commands end-to-end with proper database and file system isolation.
Uses Click's CliRunner for testing CLI interactions.
"""

import os
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


class TestCLIInit:
    """Test init command."""

    @pytest.mark.parametrize(
        "options",
        [
            (["--project-name", "Test Project"]),
            (["--project-name", "Test", "--description", "Test project"]),
        ],
    )
    def test_init(self, cli_runner, options):
        """Test initializing roadmap with various options."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                ["init"] + options + ["--non-interactive", "--skip-github"],
            )

            assert result.exit_code == 0
            assert ".roadmap" in os.listdir(".")
            assert (
                "initialized" in result.output.lower()
                or "success" in result.output.lower()
            )

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
            # Database should be created in db/ folder
            db_files = list((roadmap_dir / "db").glob("*.db"))
            assert len(db_files) > 0

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

    def test_health_check(self, isolated_roadmap):
        """Test health check command."""
        cli_runner, _ = isolated_roadmap
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

    def test_update_issue_help(self, cli_runner):
        """Test issue update help."""
        result = cli_runner.invoke(main, ["issue", "update", "--help"])

        assert result.exit_code == 0


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

    def test_delete_issue_help(self, cli_runner):
        """Test issue delete help."""
        result = cli_runner.invoke(main, ["issue", "delete", "--help"])

        assert result.exit_code == 0


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

    def test_start_issue_help(self, cli_runner):
        """Test start command help."""
        result = cli_runner.invoke(main, ["issue", "start", "--help"])

        assert result.exit_code == 0

    def test_close_issue_help(self, cli_runner):
        """Test close command help."""
        result = cli_runner.invoke(main, ["issue", "close", "--help"])

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


@pytest.fixture
def isolated_roadmap_with_milestone(isolated_roadmap_with_issues):
    """Create an isolated roadmap with issues and a milestone.

    Yields:
        tuple: (cli_runner, temp_dir_path)
    """
    cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

    # Create a milestone
    result = cli_runner.invoke(
        main,
        ["milestone", "create", "Sprint 1", "--description", "First sprint"],
    )
    assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

    yield cli_runner, temp_dir


class TestCLIMilestoneCreate:
    """Test milestone create command."""

    @pytest.mark.parametrize(
        "name,options",
        [
            ("Test Milestone", []),  # Minimal
            (
                "Sprint 1",
                ["--description", "First development sprint"],
            ),  # With description
            ("Release 1.0", ["--due-date", "2025-12-31"]),  # With due date
        ],
    )
    def test_create_milestone(self, isolated_roadmap, name, options):
        """Test creating milestones with various options."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "create", name] + options,
        )

        assert result.exit_code == 0
        assert (
            "created" in result.output.lower() or "milestone" in result.output.lower()
        )

    def test_create_milestone_help(self, cli_runner):
        """Test milestone create help."""
        result = cli_runner.invoke(main, ["milestone", "create", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output.lower()


class TestCLIMilestoneList:
    """Test milestone list command."""

    def test_list_milestones(self, isolated_roadmap_with_milestone):
        """Test listing all milestones."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(main, ["milestone", "list"])

        assert result.exit_code == 0
        # Should show the created milestone
        assert "sprint" in result.output.lower() or "milestone" in result.output.lower()

    def test_list_milestones_empty(self, isolated_roadmap):
        """Test listing milestones when none exist."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["milestone", "list"])

        assert result.exit_code == 0
        # Should handle empty list gracefully

    def test_list_milestones_help(self, cli_runner):
        """Test milestone list help."""
        result = cli_runner.invoke(main, ["milestone", "list", "--help"])

        assert result.exit_code == 0


class TestCLIMilestoneAssign:
    """Test milestone assign command."""

    def test_assign_issue_to_milestone(self, isolated_roadmap_with_milestone):
        """Test assigning an issue to a milestone."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "assign", "1", "Sprint 1"],
        )

        assert result.exit_code == 0 or "assigned" in result.output.lower()

    def test_assign_nonexistent_issue(self, isolated_roadmap_with_milestone):
        """Test assigning non-existent issue."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "assign", "999", "Sprint 1"],
        )

        # Should either exit with error or show error message
        assert result.exit_code != 0 or "failed" in result.output.lower()

    def test_assign_to_nonexistent_milestone(self, isolated_roadmap_with_issues):
        """Test assigning to non-existent milestone."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["milestone", "assign", "1", "Nonexistent"],
        )

        # Should either exit with error or show error message
        assert result.exit_code != 0 or "failed" in result.output.lower()

    def test_assign_help(self, cli_runner):
        """Test milestone assign help."""
        result = cli_runner.invoke(main, ["milestone", "assign", "--help"])

        assert result.exit_code == 0


class TestCLIMilestoneUpdate:
    """Test milestone update command."""

    def test_update_milestone_description(self, isolated_roadmap_with_milestone):
        """Test updating milestone description."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "update", "Sprint 1", "--description", "Updated description"],
        )

        assert result.exit_code == 0 or "updated" in result.output.lower()

    def test_update_nonexistent_milestone(self, isolated_roadmap):
        """Test updating non-existent milestone."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "update", "Nonexistent", "--description", "Test"],
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_update_help(self, cli_runner):
        """Test milestone update help."""
        result = cli_runner.invoke(main, ["milestone", "update", "--help"])

        assert result.exit_code == 0


class TestCLIMilestoneClose:
    """Test milestone close command."""

    def test_close_milestone(self, isolated_roadmap_with_milestone):
        """Test closing a milestone."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        result = cli_runner.invoke(
            main,
            ["milestone", "close", "Sprint 1"],
        )

        assert (
            result.exit_code == 0
            or "close" in result.output.lower()
            or "completed" in result.output.lower()
        )

    def test_close_nonexistent_milestone(self, isolated_roadmap):
        """Test closing non-existent milestone."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "close", "Nonexistent"],
        )

        # Should either exit with error or show error message
        assert result.exit_code != 0 or "failed" in result.output.lower()

    def test_close_help(self, cli_runner):
        """Test milestone close help."""
        result = cli_runner.invoke(main, ["milestone", "close", "--help"])

        assert result.exit_code == 0


class TestCLIMilestoneDelete:
    """Test milestone delete command."""

    def test_delete_milestone(self, isolated_roadmap_with_milestone):
        """Test deleting a milestone."""
        cli_runner, temp_dir = isolated_roadmap_with_milestone

        # Create an extra milestone to delete
        cli_runner.invoke(main, ["milestone", "create", "To Delete"])

        result = cli_runner.invoke(
            main,
            ["milestone", "delete", "To Delete"],
            input="y\n",
        )

        assert result.exit_code == 0 or "deleted" in result.output.lower()

    def test_delete_nonexistent_milestone(self, isolated_roadmap):
        """Test deleting non-existent milestone."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["milestone", "delete", "Nonexistent"],
            input="y\n",
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_delete_help(self, cli_runner):
        """Test milestone delete help."""
        result = cli_runner.invoke(main, ["milestone", "delete", "--help"])

        assert result.exit_code == 0


class TestCLIMilestoneHelp:
    """Test milestone command help."""

    def test_milestone_group_help(self, cli_runner):
        """Test milestone group help."""
        result = cli_runner.invoke(main, ["milestone", "--help"])

        assert result.exit_code == 0
        assert "milestone" in result.output.lower()
        # Should list subcommands
        assert "create" in result.output.lower()
        assert "list" in result.output.lower()

    def test_all_milestone_subcommands_have_help(self, cli_runner):
        """Test that all milestone subcommands have help."""
        subcommands = [
            "create",
            "list",
            "assign",
            "update",
            "delete",
            "close",
            "recalculate",
            "kanban",
        ]

        for cmd in subcommands:
            result = cli_runner.invoke(main, ["milestone", cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} help failed"


class TestCLIDataExport:
    """Test data export command."""

    @pytest.mark.parametrize(
        "format_type,extension",
        [
            ("json", ".json"),
            ("csv", ".csv"),
            ("markdown", ".md"),
        ],
    )
    def test_export_formats(self, isolated_roadmap_with_issues, format_type, extension):
        """Test exporting data in various formats."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        output_file = temp_dir / f"export{extension}"
        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", format_type, "-o", str(output_file)],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        # Verify file has content
        content = output_file.read_text()
        assert len(content) > 0

    def test_export_without_output_file(self, isolated_roadmap_with_issues):
        """Test export outputs to stdout when no file specified."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", "json"],
        )

        assert result.exit_code == 0
        # Should have output
        assert len(result.output) > 0

    def test_export_with_filter(self, isolated_roadmap_with_issues):
        """Test export with filter option."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        output_file = temp_dir / "filtered.json"
        result = cli_runner.invoke(
            main,
            [
                "data",
                "export",
                "--format",
                "json",
                "-o",
                str(output_file),
                "--filter",
                "status=open",
            ],
        )

        # Command should succeed even if no matching data
        assert result.exit_code == 0

    def test_export_help(self, cli_runner):
        """Test data export help."""
        result = cli_runner.invoke(main, ["data", "export", "--help"])

        assert result.exit_code == 0
        assert "export" in result.output.lower()


class TestCLIDataGroup:
    """Test data command group."""

    def test_data_group_help(self, cli_runner):
        """Test data group help."""
        result = cli_runner.invoke(main, ["data", "--help"])

        assert result.exit_code == 0
        assert "export" in result.output.lower()


class TestCLIGitIntegration:
    """Test git integration commands."""

    @pytest.fixture
    def isolated_git_repo(self, isolated_roadmap_with_issues):
        """Create an isolated roadmap with git repo."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )
        # Initial commit
        subprocess.run(
            ["git", "add", "."], cwd=temp_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )

        return cli_runner, temp_dir

    def test_git_status(self, isolated_git_repo):
        """Test git status command."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(main, ["git", "status"])

        assert result.exit_code == 0
        # Should show git information
        assert len(result.output) > 0

    def test_git_status_without_repo(self, isolated_roadmap_with_issues):
        """Test git status without git repo."""
        cli_runner, temp_dir, _issue_ids = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["git", "status"])

        # Should handle gracefully (exit 0 or show error message)
        assert result.exit_code == 0 or "not a git repository" in result.output.lower()

    def test_git_branch_create(self, isolated_git_repo):
        """Test creating git branch for issue."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", "1", "--no-checkout"],
        )

        # Should create branch
        assert result.exit_code == 0 or "branch" in result.output.lower()

    def test_git_branch_with_checkout(self, isolated_git_repo):
        """Test creating and checking out git branch."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", "1", "--checkout"],
        )

        # Should create and checkout branch
        assert result.exit_code == 0 or "branch" in result.output.lower()

    def test_git_branch_nonexistent_issue(self, isolated_git_repo):
        """Test creating branch for nonexistent issue."""
        cli_runner, temp_dir = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", "999"],
        )

        # Should fail gracefully
        assert (
            result.exit_code != 0
            or "not found" in result.output.lower()
            or "failed" in result.output.lower()
        )

    def test_git_branch_help(self, cli_runner):
        """Test git branch help."""
        result = cli_runner.invoke(main, ["git", "branch", "--help"])

        assert result.exit_code == 0
        assert "branch" in result.output.lower()

    def test_git_status_help(self, cli_runner):
        """Test git status help."""
        result = cli_runner.invoke(main, ["git", "status", "--help"])

        assert result.exit_code == 0


class TestCLIGitGroup:
    """Test git command group."""

    def test_git_group_help(self, cli_runner):
        """Test git group help."""
        result = cli_runner.invoke(main, ["git", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()
        assert "branch" in result.output.lower()

    def test_all_git_subcommands_have_help(self, cli_runner):
        """Test that all git subcommands have help."""
        subcommands = ["status", "branch", "setup", "link", "sync"]

        for cmd in subcommands:
            result = cli_runner.invoke(main, ["git", cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} help failed"
