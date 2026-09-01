"""Integration tests for CLI commands.

Integration tests for root/help CLI commands.

Uses Click's CliRunner for testing CLI interactions.
"""

import json
import os
from pathlib import Path

import pytest

from roadmap.bootstrap import cli as main
from tests.fixtures.ansi import clean_cli_output
from tests.fixtures.integration_helpers import IntegrationTestBase


def _output_lower(result) -> str:
    return clean_cli_output(result.output).lower()


def _output(result) -> str:
    return clean_cli_output(result.output)


@pytest.fixture
def isolated_roadmap(cli_runner):
    """Create an isolated roadmap environment with initialized database.

    Yields:
        tuple: (cli_runner, roadmap_core)
    """
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)
        yield cli_runner, core
        # Cleanup happens here when context exits


@pytest.fixture
def isolated_roadmap_with_issues(cli_runner):
    """Create an isolated roadmap with sample issues.

    Yields:
        tuple: (cli_runner, roadmap_core)
    """
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)

        # Create a few test issues
        for title, priority in [
            ("Fix bug in parser", "high"),
            ("Add new feature", "medium"),
            ("Update documentation", "low"),
        ]:
            IntegrationTestBase.create_issue(cli_runner, title=title, priority=priority)

        yield cli_runner, core
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
                ],
                lambda result: (
                    result.exit_code == 0
                    and ".roadmap" in os.listdir(".")
                    and (
                        "initialized" in _output_lower(result)
                        or "success" in _output_lower(result)
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
                ],
                lambda result: (
                    result.exit_code == 0
                    and ".roadmap" in os.listdir(".")
                    and (
                        "initialized" in _output_lower(result)
                        or "success" in _output_lower(result)
                    )
                ),
            ),
            (
                [
                    "init",
                    "--project-name",
                    "Test",
                    "--non-interactive",
                ],
                lambda result: result.exit_code == 0 and Path(".roadmap").exists(),
            ),
            (
                ["init", "--help"],
                lambda result: (
                    result.exit_code == 0
                    and "init" in _output_lower(result)
                    and "project" in _output_lower(result)
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
                    "not initialized" in _output_lower(result) or result.exit_code != 0
                ),
            ),
            (
                ["status"],
                "init",
                lambda result: (
                    result.exit_code == 0
                    and (
                        "roadmap" in _output_lower(result)
                        or "status" in _output_lower(result)
                    )
                ),
            ),
            (
                ["status", "--help"],
                "no_init",
                lambda result: (
                    result.exit_code == 0 and "status" in _output_lower(result)
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
            cli_runner2, _core = isolated_roadmap
            result = cli_runner2.invoke(main, cmd)
            assert check(result)

    def test_status_json_is_versioned_and_deterministic(self, isolated_roadmap):
        cli_runner, _core = isolated_roadmap

        first = cli_runner.invoke(main, ["status", "--format", "json"])
        second = cli_runner.invoke(main, ["status", "--format", "json"])

        assert first.exit_code == 0
        assert first.stdout == second.stdout
        payload = json.loads(first.stdout)
        assert payload["schema_version"] == 1
        assert payload["kind"] == "roadmap.status"


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
                    result.exit_code in {0, 1}
                    and (
                        "health" in _output_lower(result)
                        or "status" in _output_lower(result)
                        or "ok" in _output_lower(result)
                    )
                ),
            ),
            (["health", "--help"], "no_init", lambda result: result.exit_code == 0),
        ],
    )
    def test_health_variants(self, cli_runner, isolated_roadmap, cmd, env, check):
        if env == "no_init":
            result = cli_runner.invoke(main, cmd)
            assert check(result)
        else:
            cli_runner2, _core = isolated_roadmap
            result = cli_runner2.invoke(main, cmd)
            assert check(result)

    def test_health_json_and_confirmed_projection_repair(self, isolated_roadmap):
        cli_runner, _core = isolated_roadmap

        Path(".roadmap/db/projection.db.stale").write_text(
            "test fixture: canonical state is newer\n", encoding="utf-8"
        )

        before = cli_runner.invoke(main, ["health", "--format", "json"])
        preview = cli_runner.invoke(
            main,
            [
                "health",
                "fix",
                "--fix-type",
                "projection",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        applied = cli_runner.invoke(
            main,
            ["health", "fix", "--fix-type", "projection", "--yes", "--format", "json"],
        )

        before_payload = json.loads(before.stdout)
        preview_payload = json.loads(preview.stdout)
        applied_payload = json.loads(applied.stdout)
        assert before_payload["kind"] == "roadmap.health"
        assert preview_payload["mode"] == "dry-run"
        assert preview_payload["actions"][0]["action_id"] == "rebuild-projection"
        assert applied.exit_code == 0
        assert applied_payload["post_check"]["status"] == "healthy"


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
        assert expected_keyword in _output_lower(result)


class TestCLIRootHelp:
    """Test root CLI help."""

    def test_root_help(self, cli_runner):
        """Test root help command."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "roadmap" in _output_lower(result)

    def test_no_command_shows_help(self, cli_runner):
        """Test that running without command shows help."""
        result = cli_runner.invoke(main, [])

        # Click may return exit code 0 (help) or 2 (missing command)
        assert result.exit_code in [0, 2]
        output = _output_lower(result)
        assert "roadmap" in output or "usage" in output

    def test_version_flag(self, cli_runner):
        """Test --version flag."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        # Should show version info
        assert "version" in _output_lower(result) or len(_output(result).strip()) > 0


@pytest.fixture
def isolated_roadmap_with_milestone(cli_runner):
    """Create an isolated roadmap with issues and a milestone.

    Yields:
        tuple: (cli_runner, roadmap_core)
    """
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)

        # Create some issues
        for title, priority in [
            ("Fix bug in parser", "high"),
            ("Add new feature", "medium"),
            ("Update documentation", "low"),
        ]:
            IntegrationTestBase.create_issue(cli_runner, title=title, priority=priority)

        # Create a milestone
        IntegrationTestBase.create_milestone(
            cli_runner, name="sprint-1", headline="First sprint"
        )

        yield cli_runner, core
