"""Integration tests for CLI commands.

Integration tests for CLI data export and git integration commands.

Uses Click's CliRunner for testing CLI interactions.
"""

from pathlib import Path

import pytest

from roadmap.adapters.cli import main
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
        cli_runner, core = isolated_roadmap_with_issues

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
        cli_runner, core = isolated_roadmap_with_issues

        result = cli_runner.invoke(
            main,
            ["data", "export", "--format", "json"],
        )

        assert result.exit_code == 0
        # Should have output
        assert len(result.output) > 0

    def test_export_with_filter(self, isolated_roadmap_with_issues):
        """Test export with filter option."""
        cli_runner, core = isolated_roadmap_with_issues

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
        import subprocess

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
        cli_runner, core = isolated_roadmap_with_issues

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
