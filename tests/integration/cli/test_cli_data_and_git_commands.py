"""Integration tests for CLI commands.

Integration tests for CLI data export and git integration commands.

Uses Click's CliRunner for testing CLI interactions.
"""

import csv
import io
import json
import subprocess
from pathlib import Path

import pytest

from roadmap.bootstrap import cli as main
from tests.fixtures.integration_helpers import IntegrationTestBase


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
        cli_runner, _core = isolated_roadmap_with_issues

        output_file = Path.cwd() / f"export{extension}"
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
        cli_runner, _core = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", "json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["schema_version"] == 1
        assert payload["kind"] == "roadmap.issue-export"
        assert [item["id"] for item in payload["issues"]] == sorted(
            item["id"] for item in payload["issues"]
        )
        assert "Exporting" not in result.stdout

    def test_export_with_filter(self, isolated_roadmap_with_issues):
        """Test export with filter option."""
        cli_runner, _core = isolated_roadmap_with_issues

        output_file = Path.cwd() / "filtered.json"
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

    def test_empty_export_is_valid_and_versioned(self, isolated_roadmap):
        cli_runner, _core = isolated_roadmap

        json_result = cli_runner.invoke(main, ["data", "export", "--format", "json"])
        csv_result = cli_runner.invoke(main, ["data", "export", "--format", "csv"])

        assert json.loads(json_result.stdout) == {
            "issues": [],
            "kind": "roadmap.issue-export",
            "schema_version": 1,
        }
        rows = list(csv.DictReader(io.StringIO(csv_result.stdout)))
        assert rows == []
        assert "schema_version" in csv_result.stdout.splitlines()[0]

    def test_export_refuses_to_overwrite(self, isolated_roadmap_with_issues):
        cli_runner, _core = isolated_roadmap_with_issues
        output_file = Path.cwd() / "existing.json"
        output_file.write_text("keep me\n", encoding="utf-8")

        result = cli_runner.invoke(
            main, ["data", "export", "--format", "json", "-o", str(output_file)]
        )

        assert result.exit_code != 0
        assert output_file.read_text(encoding="utf-8") == "keep me\n"

    def test_export_rejects_unknown_filter(self, isolated_roadmap_with_issues):
        cli_runner, _core = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["data", "export", "--filter", "wat=nope"])

        assert result.exit_code != 0
        assert result.stdout == ""

    def test_json_export_preserves_unicode_and_explicit_nulls(
        self, isolated_roadmap_with_issues
    ):
        cli_runner, _core = isolated_roadmap_with_issues
        IntegrationTestBase.create_issue(cli_runner, title="Résumé planning 🚀")

        result = cli_runner.invoke(main, ["data", "export", "--format", "json"])

        assert result.exit_code == 0
        exported = next(
            issue
            for issue in json.loads(result.stdout)["issues"]
            if issue["title"] == "Résumé planning 🚀"
        )
        assert exported["assignee"] is None or isinstance(exported["assignee"], str)
        assert exported["due_at"] is None
        assert exported["milestone_id"] is None


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
        cli_runner, core = isolated_roadmap_with_issues

        # Initialize git repo
        temp_dir = Path.cwd()
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

        issue_id = str(core.issue_queries.ids()[0])
        return cli_runner, temp_dir, core, issue_id

    def test_git_status(self, isolated_git_repo):
        """Test git status command."""
        cli_runner, _temp_dir, _core, _issue_id = isolated_git_repo

        result = cli_runner.invoke(main, ["git", "status"])

        assert result.exit_code == 0
        # Should show git information
        assert len(result.output) > 0

    def test_git_status_without_repo(self, isolated_roadmap_with_issues):
        """Test git status without git repo."""
        cli_runner, _core = isolated_roadmap_with_issues

        result = cli_runner.invoke(main, ["git", "status"])

        # Should handle gracefully (exit 0 or show error message)
        assert result.exit_code == 0 or "not a git repository" in result.output.lower()

    def test_git_branch_create(self, isolated_git_repo):
        """Test creating git branch for issue."""
        cli_runner, temp_dir, core, issue_id = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", issue_id, "--no-checkout"],
        )

        assert result.exit_code == 0, result.output
        branch = result.output.split("Created branch: ", 1)[1].splitlines()[0]
        branches = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        assert branch in branches
        assert branch in core.issue_queries.view(issue_id).issue.git_branches

    def test_git_branch_with_checkout(self, isolated_git_repo):
        """Test creating and checking out git branch."""
        cli_runner, temp_dir, core, issue_id = isolated_git_repo

        result = cli_runner.invoke(
            main,
            ["git", "branch", issue_id, "--checkout"],
        )

        assert result.exit_code == 0, result.output
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert branch.startswith(f"issue/{issue_id}-")
        assert branch in core.issue_queries.view(issue_id).issue.git_branches

    def test_git_link_current_branch(self, isolated_git_repo):
        cli_runner, temp_dir, core, issue_id = isolated_git_repo
        subprocess.run(
            ["git", "switch", "-c", "work/manual-link"],
            cwd=temp_dir,
            check=True,
            capture_output=True,
        )

        result = cli_runner.invoke(main, ["git", "link", issue_id])

        assert result.exit_code == 0, result.output
        assert (
            "work/manual-link" in core.issue_queries.view(issue_id).issue.git_branches
        )

    def test_git_branch_nonexistent_issue(self, isolated_git_repo):
        """Test creating branch for nonexistent issue."""
        cli_runner, _temp_dir, _core, _issue_id = isolated_git_repo

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
        subcommands = ["status", "branch", "link"]

        for cmd in subcommands:
            result = cli_runner.invoke(main, ["git", cmd, "--help"])
            assert result.exit_code == 0, f"{cmd} help failed"

    def test_git_group_excludes_remote_auth_and_hook_commands(self, cli_runner):
        result = cli_runner.invoke(main, ["git", "--help"])

        assert result.exit_code == 0
        for removed in ("setup", "sync", "auth", "hooks", "connectivity"):
            assert removed not in result.output.lower()
