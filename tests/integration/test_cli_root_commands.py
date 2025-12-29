"""Integration tests for CLI commands.

Integration tests for root/help CLI commands.

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

    import pytest

    @pytest.mark.parametrize(
        "cmd,check",
        [
            (
                [
                    "init",
                    "--project-name",
                    "Test Project",
                    "--non-interactive",
                    "--skip-github",
                ],
                lambda result: (
                    result.exit_code == 0
                    and ".roadmap" in os.listdir(".")
                    and (
                        "initialized" in result.output.lower()
                        or "success" in result.output.lower()
                    )
                ),
            ),
            (
                [
                    "init",
                    "--project-name",
                    "Test",
                    "--description",
                    "Test project",
                    "--non-interactive",
                    "--skip-github",
                ],
                lambda result: (
                    result.exit_code == 0
                    and ".roadmap" in os.listdir(".")
                    and (
                        "initialized" in result.output.lower()
                        or "success" in result.output.lower()
                    )
                ),
            ),
            (
                [
                    "init",
                    "--project-name",
                    "Test",
                    "--non-interactive",
                    "--skip-github",
                ],
                lambda result: (
                    Path(".roadmap").exists()
                    and len(list((Path(".roadmap") / "db").glob("*.db"))) > 0
                ),
            ),
            (
                ["init", "--help"],
                lambda result: (
                    result.exit_code == 0
                    and "init" in result.output.lower()
                    and "project" in result.output.lower()
                ),
            ),
        ],
    )
    def test_init_variants(self, cli_runner, cmd, check):
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, cmd)
            assert check(result)


class TestCLIStatus:
    """Test status command."""

    import pytest

    @pytest.mark.parametrize(
        "cmd,env,check",
        [
            (
                ["status"],
                "no_init",
                lambda result: (
                    "not initialized" in result.output.lower() or result.exit_code != 0
                ),
            ),
            (
                ["status"],
                "init",
                lambda result: (
                    result.exit_code == 0
                    and (
                        "roadmap" in result.output.lower()
                        or "status" in result.output.lower()
                    )
                ),
            ),
            (
                ["status", "--help"],
                "no_init",
                lambda result: (
                    result.exit_code == 0 and "status" in result.output.lower()
                ),
            ),
        ],
    )
    def test_status_variants(self, cli_runner, isolated_roadmap, cmd, env, check):
        if env == "no_init":
            with cli_runner.isolated_filesystem():
                result = cli_runner.invoke(main, cmd)
                assert check(result)
        else:
            cli_runner2, temp_dir = isolated_roadmap
            result = cli_runner2.invoke(main, cmd)
            assert check(result)


class TestCLIHealth:
    """Test health command."""

    import pytest

    @pytest.mark.parametrize(
        "cmd,env,check",
        [
            (
                ["health"],
                "init",
                lambda result: (
                    result.exit_code == 0
                    and (
                        "health" in result.output.lower()
                        or "status" in result.output.lower()
                        or "ok" in result.output.lower()
                    )
                ),
            ),
            (["health", "--help"], "no_init", lambda result: (result.exit_code == 0)),
        ],
    )
    def test_health_variants(self, cli_runner, isolated_roadmap, cmd, env, check):
        if env == "no_init":
            result = cli_runner.invoke(main, cmd)
            assert check(result)
        else:
            cli_runner2, _ = isolated_roadmap
            result = cli_runner2.invoke(main, cmd)
            assert check(result)


class TestCLIHelpCommands:
    """Test help functionality across CLI commands."""

    @pytest.mark.parametrize(
        "cmd_path,expected_keyword",
        [
            (["issue", "list", "--help"], "list"),
            (["issue", "update", "--help"], "update"),
            (["issue", "delete", "--help"], "delete"),
            (["issue", "start", "--help"], "start"),
            (["issue", "close", "--help"], "close"),
            (["milestone", "create", "--help"], "create"),
            (["milestone", "list", "--help"], "list"),
            (["milestone", "assign", "--help"], "assign"),
            (["milestone", "update", "--help"], "update"),
            (["milestone", "close", "--help"], "close"),
            (["milestone", "delete", "--help"], "delete"),
            (["data", "export", "--help"], "export"),
            (["git", "status", "--help"], "status"),
            (["git", "branch", "--help"], "branch"),
        ],
    )
    def test_command_help_output(self, cli_runner, cmd_path, expected_keyword):
        """Test that commands produce valid help output."""
        result = cli_runner.invoke(main, cmd_path)
        assert result.exit_code == 0
        assert expected_keyword in result.output.lower()


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
