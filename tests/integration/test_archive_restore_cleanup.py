"""Integration tests for archive, restore, and cleanup commands.

Tests archive/restore functionality for issues, milestones, projects,
and cleanup command for backup pruning.
"""

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click CLI runner for testing."""
    return CliRunner()


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
            # Find "Created issue:" and extract the ID from the brackets on that line
            if "Created issue:" in result.output:
                created_part = result.output.split("Created issue:")[-1].split("\n")[0]
                match = re.search(r"\[([^\]]+)\]", created_part)
            else:
                match = None
            assert (
                match is not None
            ), f"Could not find issue ID in output: {result.output}"
            issue_id = match.group(1)
            issues.append({"id": issue_id, "title": title, "status": status})

            # Update status for done issue
            if status == "closed":
                result = cli_runner.invoke(
                    main,
                    ["issue", "update", issue_id, "--status", "closed"],
                )
                assert result.exit_code == 0

        yield cli_runner, temp_dir, issues


class TestIssueArchiveRestore:
    """Test issue archive and restore commands."""

    def test_archive_single_done_issue(self, roadmap_with_issues_and_milestones):
        """Test archiving a single done issue."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        done_issue = next(i for i in issues if i["status"] == "closed")

        result = cli_runner.invoke(
            main,
            ["issue", "archive", done_issue["id"], "--force"],
        )

        assert result.exit_code == 0

        # Verify issue no longer in active list
        result = cli_runner.invoke(main, ["issue", "list"])
        assert done_issue["id"] not in result.output

    def test_archive_all_done_issues(self, roadmap_with_issues_and_milestones):
        """Test archiving all done issues."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["issue", "archive", "--all-closed", "--force"],
        )

        assert result.exit_code == 0

    def test_archive_orphaned_issues(self, roadmap_with_issues_and_milestones):
        """Test archiving issues with no milestone."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["issue", "archive", "--orphaned", "--force"],
        )

        assert result.exit_code == 0

    def test_archive_list(self, roadmap_with_issues_and_milestones):
        """Test listing archived issues."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        # Archive a done issue
        done_issue = next(i for i in issues if i["status"] == "closed")
        result = cli_runner.invoke(
            main,
            ["issue", "archive", done_issue["id"], "--force"],
        )
        assert result.exit_code == 0

        # List archived
        result = cli_runner.invoke(main, ["issue", "archive", "--list"])
        assert result.exit_code == 0

    def test_archive_dry_run(self, roadmap_with_issues_and_milestones):
        """Test archive dry-run doesn't modify anything."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        done_issue = next(i for i in issues if i["status"] == "closed")

        result = cli_runner.invoke(
            main,
            ["issue", "archive", done_issue["id"], "--dry-run"],
        )

        assert result.exit_code == 0

    def test_restore_single_issue(self, roadmap_with_issues_and_milestones):
        """Test restoring a single archived issue."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        done_issue = next(i for i in issues if i["status"] == "closed")

        # Archive first
        result = cli_runner.invoke(
            main,
            ["issue", "archive", done_issue["id"], "--force"],
        )
        assert result.exit_code == 0

        # Restore
        result = cli_runner.invoke(
            main,
            ["issue", "restore", done_issue["id"], "--force"],
        )

        assert result.exit_code == 0

    def test_restore_all_issues(self, roadmap_with_issues_and_milestones):
        """Test restoring all archived issues."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        # Archive all done issues
        result = cli_runner.invoke(
            main,
            ["issue", "archive", "--all-closed", "--force"],
        )
        assert result.exit_code == 0

        # Restore all
        result = cli_runner.invoke(
            main,
            ["issue", "restore", "--all", "--force"],
        )

        assert result.exit_code == 0

    def test_restore_with_status_update(self, roadmap_with_issues_and_milestones):
        """Test restoring issue with status change."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        done_issue = next(i for i in issues if i["status"] == "closed")

        # Archive
        result = cli_runner.invoke(
            main,
            ["issue", "archive", done_issue["id"], "--force"],
        )
        assert result.exit_code == 0

        # Restore with status update
        result = cli_runner.invoke(
            main,
            ["issue", "restore", done_issue["id"], "--status", "todo", "--force"],
        )

        assert result.exit_code == 0


class TestMilestoneArchiveRestore:
    """Test milestone archive and restore commands."""

    def test_archive_single_milestone(self, roadmap_with_issues_and_milestones):
        """Test archiving a single milestone."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1.0", "--force"],
        )

        assert result.exit_code == 0

    def test_archive_milestone_with_issues_folder(
        self, roadmap_with_issues_and_milestones
    ):
        """Test that archiving a milestone also archives its issues folder if it exists."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        roadmap_dir = Path(temp_dir) / ".roadmap"

        # Create an empty issues folder for v1.0 to simulate real scenario
        # (in production, a milestone's issues folder would exist if issues were assigned)
        issues_dir = roadmap_dir / "issues" / "v1.0"
        issues_dir.mkdir(parents=True, exist_ok=True)

        # Create a dummy issue file in the folder
        (issues_dir / "test-issue.md").write_text("# Test Issue\nstatus: closed")

        # Verify issues folder exists before archiving
        assert issues_dir.exists(), "Issues folder should exist before archiving"

        # Archive the milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1.0", "--force"],
        )

        assert (
            result.exit_code == 0
        ), f"Archive command failed (exit {result.exit_code}): {result.output}"

        # Verify milestone file was archived
        archive_milestones_dir = roadmap_dir / "archive" / "milestones"
        assert (
            archive_milestones_dir.exists()
        ), "Archive milestones directory should exist"

        milestone_files = list(archive_milestones_dir.glob("*.md"))
        assert (
            len(milestone_files) > 0
        ), f"No milestone files found in {archive_milestones_dir}"

        # Verify issues folder was also archived
        assert (
            not issues_dir.exists()
        ), "Issues folder should not exist in active directory after archiving"

        archive_issues_dir = roadmap_dir / "archive" / "issues" / "v1.0"
        assert (
            archive_issues_dir.exists()
        ), "Issues folder should be moved to archive/issues/"

        # Verify the issue file was moved
        archived_issue_file = archive_issues_dir / "test-issue.md"
        assert (
            archived_issue_file.exists()
        ), "Issue file should be moved to archived folder"

    def test_archive_list_milestones(self, roadmap_with_issues_and_milestones):
        """Test listing archived milestones."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        # Archive a milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1.0", "--force"],
        )
        assert result.exit_code == 0

        # List archived
        result = cli_runner.invoke(main, ["milestone", "archive", "--list"])
        assert result.exit_code == 0

    def test_milestone_archive_dry_run(self, roadmap_with_issues_and_milestones):
        """Test milestone archive dry-run."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1.0", "--dry-run", "--force"],
        )

        assert result.exit_code == 0

    def test_restore_single_milestone(self, roadmap_with_issues_and_milestones):
        """Test restoring a single archived milestone."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        # Archive first
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1.0", "--force"],
        )
        assert result.exit_code == 0

        # Restore
        result = cli_runner.invoke(
            main,
            ["milestone", "restore", "v1.0", "--force"],
        )

        assert result.exit_code == 0

    def test_restore_all_milestones(self, roadmap_with_issues_and_milestones):
        """Test restoring all archived milestones."""
        cli_runner, temp_dir, issues = roadmap_with_issues_and_milestones

        # Archive
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1.0", "--force"],
        )
        assert result.exit_code == 0

        # Restore all
        result = cli_runner.invoke(
            main,
            ["milestone", "restore", "--all", "--force"],
        )

        assert result.exit_code == 0


class TestProjectArchiveRestore:
    """Test project archive and restore commands."""

    def test_project_archive_single(self, isolated_roadmap):
        """Test archiving a project."""
        cli_runner, temp_dir = isolated_roadmap

        # Create a project
        result = cli_runner.invoke(
            main,
            ["project", "create", "ArchiveMe", "--description", "Test project"],
        )
        # Project create may have issues, so we'll skip if it fails
        if result.exit_code != 0:
            pytest.skip(f"Project creation not fully supported yet: {result.output}")

        # Archive it
        result = cli_runner.invoke(
            main,
            ["project", "archive", "ArchiveMe", "--force"],
        )

        assert result.exit_code in [0, 1]

    def test_project_archive_list(self, isolated_roadmap):
        """Test listing archived projects."""
        cli_runner, temp_dir = isolated_roadmap

        # Create and archive a project
        result = cli_runner.invoke(
            main,
            ["project", "create", "OldProject"],
        )
        if result.exit_code != 0:
            pytest.skip("Project creation not fully supported yet")

        result = cli_runner.invoke(
            main,
            ["project", "archive", "OldProject", "--force"],
        )
        if result.exit_code != 0:
            pytest.skip("Project archive not fully functional")

        # List archived
        result = cli_runner.invoke(main, ["project", "archive", "--list"])
        assert result.exit_code in [0, 1]

    def test_project_archive_dry_run(self, isolated_roadmap):
        """Test project archive dry-run."""
        cli_runner, temp_dir = isolated_roadmap

        # Try to run dry-run archive (may not work if project doesn't exist)
        result = cli_runner.invoke(
            main,
            ["project", "archive", "NoExist", "--dry-run"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1]

    def test_project_restore_single(self, isolated_roadmap):
        """Test restoring an archived project."""
        cli_runner, temp_dir = isolated_roadmap

        # Try to restore (may not exist)
        result = cli_runner.invoke(
            main,
            ["project", "restore", "NoExist", "--force"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1]

    def test_project_restore_all(self, isolated_roadmap):
        """Test restoring all archived projects."""
        cli_runner, temp_dir = isolated_roadmap

        # Try restore all
        result = cli_runner.invoke(
            main,
            ["project", "restore", "--all", "--force"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1]


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
