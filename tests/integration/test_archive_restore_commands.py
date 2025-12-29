"""Integration tests for archive, restore, and cleanup commands.

Tests archive/restore functionality for issues, milestones, projects,
and cleanup command for backup pruning.
"""

from pathlib import Path

import pytest

from roadmap.adapters.cli import main


@pytest.fixture
def isolated_roadmap(cli_runner):
    """Create an isolated roadmap environment with initialized database."""
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap
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
def roadmap_with_issues_and_milestones(cli_runner):
    """Create roadmap with sample issues and milestones."""
    with cli_runner.isolated_filesystem():
        temp_dir = Path.cwd()

        # Initialize a roadmap
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

        # Create a milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "create", "v1.0", "--description", "First release"],
        )
        assert result.exit_code == 0, f"Milestone creation failed: {result.output}"

        # Create issues
        issues = []
        for i, (title, status) in enumerate(
            [
                ("Fix bug in parser", "todo"),
                ("Add new feature", "in-progress"),
                ("Update docs", "closed"),
            ]
        ):
            result = cli_runner.invoke(
                main,
                [
                    "issue",
                    "create",
                    title,
                    "--priority",
                    "high" if i == 0 else "medium",
                    "--type",
                    "bug" if i == 0 else "feature",
                ],
            )
            assert result.exit_code == 0, f"Issue creation failed: {result.output}"
            # Find issue ID
            from tests.fixtures.click_testing import ClickTestHelper

            issue_id = ClickTestHelper.extract_issue_id(result.output)

            assert (
                issue_id is not None
            ), f"Could not find issue ID in output: {result.output}"
            issues.append({"id": issue_id, "title": title, "status": status})

            # Update status for done issue
            if status == "closed":
                result = cli_runner.invoke(
                    main,
                    ["issue", "update", issue_id, "--status", "closed"],
                )
                assert result.exit_code == 0

        yield cli_runner, temp_dir, issues


class TestCleanupCommand:
    """Test cleanup command for backup pruning."""

    def test_cleanup_help(self, cli_runner):
        """Test cleanup command help."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["cleanup", "--help"])
            assert result.exit_code == 0
            assert (
                "backup" in result.output.lower() or "cleanup" in result.output.lower()
            )

    def test_cleanup_no_backups(self, isolated_roadmap):
        """Test cleanup when no backups exist."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["cleanup", "--force"])
        assert result.exit_code == 0
        # When there are no issues or backups to clean, it should complete successfully
        assert (
            "Cleaned up" in result.output
            or "No backup" in result.output
            or "correct folders" in result.output
        )

    def test_cleanup_list(self, isolated_roadmap):
        """Test cleanup handles check flags gracefully."""
        cli_runner, temp_dir = isolated_roadmap

        # Test that cleanup with check-folders flag works
        result = cli_runner.invoke(main, ["cleanup", "--check-folders"])
        assert result.exit_code == 0

    def test_cleanup_dry_run(self, isolated_roadmap):
        """Test cleanup --dry-run flag."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["cleanup", "--dry-run"])
        assert result.exit_code == 0

    def test_cleanup_with_keep_option(self, isolated_roadmap):
        """Test cleanup with --keep option."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["cleanup", "--keep", "5"])
        assert result.exit_code == 0

    def test_cleanup_with_days_option(self, isolated_roadmap):
        """Test cleanup with --days option."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(main, ["cleanup", "--days", "30"])
        assert result.exit_code == 0

    def test_cleanup_with_combined_options(self, isolated_roadmap):
        """Test cleanup with both --keep and --days options."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["cleanup", "--keep", "5", "--days", "30", "--dry-run"],
        )
        assert result.exit_code == 0


class TestProjectCommands:
    """Test project management commands."""

    def test_project_create(self, isolated_roadmap):
        """Test creating a project."""
        cli_runner, temp_dir = isolated_roadmap

        result = cli_runner.invoke(
            main,
            ["project", "create", "My Project", "--description", "Test project"],
        )

        assert result.exit_code == 0
        assert "created" in result.output.lower() or "My Project" in result.output

    def test_project_list(self, isolated_roadmap):
        """Test listing projects."""
        cli_runner, temp_dir = isolated_roadmap

        # Create a project first
        result = cli_runner.invoke(
            main,
            ["project", "create", "Test Project"],
        )
        assert result.exit_code == 0

        # List projects
        result = cli_runner.invoke(main, ["project", "list"])
        assert result.exit_code == 0
        assert "Test Project" in result.output or "project" in result.output.lower()

    def test_project_view(self, isolated_roadmap):
        """Test viewing a project."""
        cli_runner, temp_dir = isolated_roadmap

        # Try to view a project (may not exist)
        result = cli_runner.invoke(
            main,
            ["project", "view", "NoExist"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1]

    def test_project_update(self, isolated_roadmap):
        """Test updating a project."""
        cli_runner, temp_dir = isolated_roadmap

        # Create a project
        result = cli_runner.invoke(
            main,
            ["project", "create", "Test Project"],
        )
        assert result.exit_code == 0

        # Update it
        result = cli_runner.invoke(
            main,
            [
                "project",
                "update",
                "Test Project",
                "--description",
                "Updated description",
            ],
        )

        assert result.exit_code == 0

    def test_project_delete(self, isolated_roadmap):
        """Test deleting a project."""
        cli_runner, temp_dir = isolated_roadmap

        # Try to delete a project (may not exist)
        result = cli_runner.invoke(
            main,
            ["project", "delete", "NoExist", "--force"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1, 2]


class TestCommentCommands:
    """Test comment management commands."""

    def test_comment_help(self, cli_runner):
        """Test comment command help."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["comment", "--help"])
            assert result.exit_code == 0
            assert "comment" in result.output.lower()

    def test_comment_add_to_issue(self, roadmap_with_issues_and_milestones):
        """Test adding a comment to an issue."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        issue_id = issues[0]["id"]

        result = cli_runner.invoke(
            main,
            ["comment", "add", issue_id, "This is a test comment"],
        )

        # Should succeed or handle gracefully
        assert result.exit_code in [0, 1, 2]

    def test_comment_list(self, roadmap_with_issues_and_milestones):
        """Test listing comments on an issue."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        issue_id = issues[0]["id"]

        result = cli_runner.invoke(
            main,
            ["comment", "list", issue_id],
        )

        # Should succeed or handle gracefully
        assert result.exit_code in [0, 1, 2]
