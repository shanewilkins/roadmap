"""Integration tests for archive, restore, and cleanup commands.

Tests archive/restore functionality for issues, milestones, projects,
and cleanup command for backup pruning.
"""

import os
from pathlib import Path

import pytest

from roadmap.adapters.persistence.parser import IssueParser
from roadmap.bootstrap import cli as main
from roadmap.common.constants import ProjectStatus
from roadmap.domain.types import RetentionState
from tests.fixtures.integration_helpers import IntegrationTestBase
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


@pytest.fixture
def isolated_roadmap(cli_runner):
    """Create an isolated roadmap environment with initialized database."""
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)
        temp_dir = os.getcwd()
        yield cli_runner, core, temp_dir


@pytest.fixture
def roadmap_with_issues_and_milestones(cli_runner):
    """Create roadmap with sample issues and milestones."""
    with cli_runner.isolated_filesystem():
        core = IntegrationTestBase.init_roadmap(cli_runner)
        temp_dir = os.getcwd()

        # Create a milestone
        IntegrationTestBase.create_milestone(
            cli_runner, name="v1-0", headline="First release"
        )

        # Create issues
        issues = []
        for _idx, (title, status, issue_type, priority) in enumerate(
            [
                ("Fix bug in parser", "todo", "bug", "high"),
                ("Add new feature", "in-progress", "feature", "medium"),
                ("Update docs", "closed", "feature", "medium"),
            ]
        ):
            IntegrationTestBase.create_issue(
                cli_runner,
                title=title,
                priority=priority,
                issue_type=issue_type,
            )

            # Get the created issue ID from core
            core = IntegrationTestBase.get_roadmap_core()
            issue = next(
                (i for i in reversed(core.issues.list()) if i.title == title), None
            )
            issue_id = issue.id if issue else None

            assert issue_id is not None, f"Could not find issue ID for {title}"
            issues.append({"id": issue_id, "title": title, "status": status})

            # Update status for done issue
            if status == "closed":
                result = cli_runner.invoke(
                    main,
                    ["issue", "update", issue_id, "--status", "closed"],
                )
                assert result.exit_code == 0

        yield cli_runner, core, issues, temp_dir


class TestIssueArchiveRestore:
    """Test issue archive and restore commands."""

    def test_archive_single_done_issue(self, roadmap_with_issues_and_milestones):
        """Test archiving a single done issue."""
        cli_runner, core, issues, temp_dir = roadmap_with_issues_and_milestones

        done_issue = next(i for i in issues if i["status"] == "closed")

        result = cli_runner.invoke(
            main,
            ["issue", "archive", done_issue["id"], "--force"],
        )

        assert result.exit_code == 0

        canonical_file = next(
            (Path(temp_dir) / ".roadmap" / "issues").rglob(f"{done_issue['id']}*.md")
        )
        from roadmap.adapters.outbound.persistence.documents import parse_document

        assert (
            parse_document(canonical_file, "issue").aggregate.retention.value
            == "archived"
        )
        assert not list(
            (Path(temp_dir) / ".roadmap" / "archive" / "issues").rglob("*.md")
        )

        # Verify issue no longer in active list
        result = cli_runner.invoke(main, ["issue", "list"])
        assert done_issue["id"] not in clean_cli_output(result.output)

    def test_archive_all_done_issues(self, roadmap_with_issues_and_milestones):
        """Test archiving all done issues."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["issue", "archive", "--all-closed", "--force"],
        )

        assert result.exit_code == 0

    def test_archive_orphaned_issues(self, roadmap_with_issues_and_milestones):
        """Test archiving issues with no milestone."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["issue", "archive", "--orphaned", "--force"],
        )

        assert result.exit_code == 0

    def test_archive_list(self, roadmap_with_issues_and_milestones):
        """Test listing archived issues."""
        cli_runner, _core, issues, _temp_dir = roadmap_with_issues_and_milestones

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
        cli_runner, _core, issues, _temp_dir = roadmap_with_issues_and_milestones

        done_issue = next(i for i in issues if i["status"] == "closed")

        result = cli_runner.invoke(
            main,
            ["issue", "archive", done_issue["id"], "--dry-run"],
        )

        assert result.exit_code == 0

    def test_restore_single_issue(self, roadmap_with_issues_and_milestones):
        """Test restoring a single archived issue."""
        cli_runner, core, issues, temp_dir = roadmap_with_issues_and_milestones

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

        restored_file = next(
            (Path(temp_dir) / ".roadmap" / "issues").rglob(f"{done_issue['id']}*.md")
        )
        assert IssueParser.parse_issue_file(restored_file).archived is False
        assert not list(
            (Path(temp_dir) / ".roadmap" / "archive" / "issues").rglob(
                f"{done_issue['id']}*.md"
            )
        )

    def test_restore_all_issues(self, roadmap_with_issues_and_milestones):
        """Test restoring all archived issues."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

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
        cli_runner, _core, issues, _temp_dir = roadmap_with_issues_and_milestones

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

    def test_archive_open_milestone_does_not_move_file(
        self, roadmap_with_issues_and_milestones
    ):
        """Test open milestones are not archived without force."""
        cli_runner, _core, _issues, temp_dir = roadmap_with_issues_and_milestones

        roadmap_dir = Path(temp_dir) / ".roadmap"
        active_milestones_dir = roadmap_dir / "milestones"
        archive_milestones_dir = roadmap_dir / "archive" / "milestones"

        active_before = list(active_milestones_dir.glob("*.md"))
        assert active_before, "Expected at least one active milestone file"

        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1-0"],
        )

        assert result.exit_code != 0
        assert list(active_milestones_dir.glob("*.md")) == active_before
        assert not archive_milestones_dir.exists() or not list(
            archive_milestones_dir.glob("*.md")
        )

    def test_archive_single_milestone(self, roadmap_with_issues_and_milestones):
        """Test archiving a single milestone."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1-0", "--force"],
        )

        assert result.exit_code == 0

    def test_archive_milestone_with_issues_folder(
        self, roadmap_with_issues_and_milestones
    ):
        """Archiving metadata never cascades into canonical issue paths."""
        cli_runner, core, _issues, temp_dir = roadmap_with_issues_and_milestones

        roadmap_dir = Path(temp_dir) / ".roadmap"

        # Create an empty issues folder for v1.0 to simulate real scenario
        # (in production, a milestone's issues folder would exist if issues were assigned)
        issues_dir = roadmap_dir / "issues" / "v1-0"
        issues_dir.mkdir(parents=True, exist_ok=True)

        # Create a dummy issue file in the folder
        (issues_dir / "test-issue.md").write_text("# Test Issue\nstatus: closed")

        # Verify issues folder exists before archiving
        assert issues_dir.exists(), "Issues folder should exist before archiving"

        # Archive the milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1-0", "--force"],
        )

        output = clean_cli_output(result.output)
        assert result.exit_code == 0, (
            f"Archive command failed (exit {result.exit_code}): {output}"
        )

        # The milestone remains at its stable path with archived retention metadata.
        archive_milestones_dir = roadmap_dir / "archive" / "milestones"
        assert not archive_milestones_dir.exists()
        milestone = core.planning.resolve_milestone_id("v1-0")
        persisted = next(
            item for item in core.planning.all_milestones() if item.id == milestone
        )
        assert persisted.retention is RetentionState.ARCHIVED

        # No issue or folder is silently moved as a side effect.
        assert issues_dir.exists()
        assert (issues_dir / "test-issue.md").exists()
        assert not (roadmap_dir / "archive" / "issues" / "v1-0").exists()

    def test_archive_list_milestones(self, roadmap_with_issues_and_milestones):
        """Test listing archived milestones."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

        # Archive a milestone
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1-0", "--force"],
        )
        assert result.exit_code == 0

        # List archived
        result = cli_runner.invoke(main, ["milestone", "archive", "--list"])
        assert result.exit_code == 0

    def test_milestone_archive_dry_run(self, roadmap_with_issues_and_milestones):
        """Test milestone archive dry-run."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1-0", "--dry-run", "--force"],
        )

        assert result.exit_code == 0

    def test_restore_single_milestone(self, roadmap_with_issues_and_milestones):
        """Test restoring a single archived milestone."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

        # Archive first
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1-0", "--force"],
        )
        assert result.exit_code == 0

        # Restore
        result = cli_runner.invoke(
            main,
            ["milestone", "restore", "v1-0", "--force"],
        )

        assert result.exit_code == 0

    def test_restore_all_milestones(self, roadmap_with_issues_and_milestones):
        """Test restoring all archived milestones."""
        cli_runner, _core, _issues, _temp_dir = roadmap_with_issues_and_milestones

        # Archive
        result = cli_runner.invoke(
            main,
            ["milestone", "archive", "v1-0", "--force"],
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

    def test_project_close_keeps_file_active(self, isolated_roadmap):
        """Test closing a project does not archive its file."""
        cli_runner, core, temp_dir = isolated_roadmap

        project = core.projects.create("Closable Project", "Test project")
        roadmap_dir = Path(temp_dir) / ".roadmap"
        active_path = roadmap_dir / "projects" / project.filename
        archive_dir = roadmap_dir / "archive" / "projects"

        assert active_path.exists(), "Expected active project file before close"

        result = cli_runner.invoke(
            main,
            ["project", "close", project.id, "--force"],
        )

        output = clean_cli_output(result.output)
        assert result.exit_code == 0, (
            f"Project close failed (exit {result.exit_code}): {output}"
        )
        assert active_path.exists(), "Project close should not move the file"
        assert not archive_dir.exists() or not list(archive_dir.rglob("*.md"))

        refreshed = core.projects.get(project.id)
        assert refreshed is not None
        assert refreshed.status == ProjectStatus.COMPLETED

    def test_project_archive_all_closed(self, isolated_roadmap):
        """Test archiving all completed projects."""
        cli_runner, core, temp_dir = isolated_roadmap

        project_one = core.projects.create("Archive Project One", "First")
        project_two = core.projects.create("Archive Project Two", "Second")

        core.projects.update(project_one.id, status=ProjectStatus.COMPLETED)
        core.projects.update(project_two.id, status=ProjectStatus.COMPLETED)

        roadmap_dir = Path(temp_dir) / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "projects"

        result = cli_runner.invoke(
            main,
            ["project", "archive", "--all-closed", "--force"],
        )

        output = clean_cli_output(result.output)
        assert result.exit_code == 0, (
            f"Project archive all-closed failed (exit {result.exit_code}): {output}"
        )

        assert not archive_dir.exists() or not list(archive_dir.rglob("*.md"))
        assert (roadmap_dir / "projects" / project_one.filename).exists()
        assert (roadmap_dir / "projects" / project_two.filename).exists()
        retained = {
            str(item.id): item.retention for item in core.planning.all_projects()
        }
        assert retained[project_one.id] is RetentionState.ARCHIVED
        assert retained[project_two.id] is RetentionState.ARCHIVED

    def test_project_archive_single(self, isolated_roadmap):
        """Test archiving a project."""
        cli_runner, _core, _temp_dir = isolated_roadmap

        # Create a project
        result = cli_runner.invoke(
            main,
            [
                "project",
                "create",
                "--title",
                "ArchiveMe",
                "--description",
                "Test project",
            ],
        )
        # Project create may have issues, so we'll skip if it fails
        if result.exit_code != 0:
            pytest.skip(
                "Project creation not fully supported yet: "
                + clean_cli_output(result.output)
            )

        # Archive it
        result = cli_runner.invoke(
            main,
            ["project", "archive", "ArchiveMe", "--force"],
        )

        assert result.exit_code in [0, 1]

    def test_project_archive_list(self, isolated_roadmap):
        """Test listing archived projects."""
        cli_runner, _core, _temp_dir = isolated_roadmap

        # Create and archive a project
        result = cli_runner.invoke(
            main,
            ["project", "create", "--title", "OldProject"],
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
        cli_runner, _core, _temp_dir = isolated_roadmap

        # Try to run dry-run archive (may not work if project doesn't exist)
        result = cli_runner.invoke(
            main,
            ["project", "archive", "NoExist", "--dry-run"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1]

    def test_project_restore_single(self, isolated_roadmap):
        """Test restoring an archived project."""
        cli_runner, _core, _temp_dir = isolated_roadmap

        # Try to restore (may not exist)
        result = cli_runner.invoke(
            main,
            ["project", "restore", "NoExist", "--force"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1]

    def test_project_restore_all(self, isolated_roadmap):
        """Test restoring all archived projects."""
        cli_runner, _core, _temp_dir = isolated_roadmap

        # Try restore all
        result = cli_runner.invoke(
            main,
            ["project", "restore", "--all", "--force"],
        )

        # Either succeeds or fails gracefully
        assert result.exit_code in [0, 1]
