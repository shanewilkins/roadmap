"""Tests to ensure archive operations don't create or leave duplicate files.

These tests verify that archiving issues doesn't result in duplicates existing
in both active and archive directories, which would cause data inconsistency.
"""

from pathlib import Path

import pytest

from roadmap.common.constants import Status
from roadmap.core.domain import Priority
from roadmap.infrastructure.coordination.core import RoadmapCore


class TestArchiveDuplicatePrevention:
    """Verify archive operations don't leave issues in both directories."""

    @pytest.fixture
    def core(self, temp_dir):
        """Create initialized roadmap core."""
        core = RoadmapCore()
        core.initialize()
        return core

    def count_active_issue_files(self, core) -> int:
        """Count all active issue markdown files recursively."""
        return len(list(core.issues_dir.glob("**/*.md")))

    def count_archived_issue_files(self, core) -> int:
        """Count all archived issue markdown files recursively."""
        archive_issues_dir = core.issues_dir.parent / "archive" / "issues"
        if not archive_issues_dir.exists():
            return 0
        return len(list(archive_issues_dir.glob("**/*.md")))

    def get_active_issue_ids(self, core) -> set:
        """Get all active issue IDs from filenames."""
        files = core.issues_dir.glob("**/*.md")
        return {Path(f).stem.split("-")[0] for f in files}

    def get_archived_issue_ids(self, core) -> set:
        """Get all archived issue IDs from filenames."""
        archive_issues_dir = core.issues_dir.parent / "archive" / "issues"
        if not archive_issues_dir.exists():
            return set()
        files = archive_issues_dir.glob("**/*.md")
        return {Path(f).stem.split("-")[0] for f in files}

    def test_archive_closed_issue_removes_from_active(self, core):
        """Ensure archiving a closed issue removes it from active directory."""
        # Create and close an issue
        issue = core.issues.create("Test Issue", priority=Priority.MEDIUM)
        core.issues.update(issue.id, status=Status.CLOSED)

        active_before = self.count_active_issue_files(core)
        assert active_before == 1, "Initial closed issue should be active"

        # Archive the closed issue
        core.issues.move_to_milestone(issue.id, None)  # Ensure it's in backlog first
        # Use the CLI to archive
        from click.testing import CliRunner

        from roadmap.adapters.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["issue", "archive", issue.id, "--force"])
        assert result.exit_code == 0, f"Archive failed: {result.output}"

        # Verify it's removed from active
        active_after = self.count_active_issue_files(core)
        assert active_after == 0, "Closed issue should be removed from active"

    def test_no_issue_ids_in_both_directories(self, core):
        """Ensure no issue appears in both active and archive directories."""
        # Create multiple issues and close some
        issue1 = core.issues.create("Issue 1", priority=Priority.MEDIUM)
        issue2 = core.issues.create("Issue 2", priority=Priority.MEDIUM)
        issue3 = core.issues.create("Issue 3", priority=Priority.MEDIUM)

        # Close issue1 and issue2
        core.issues.update(issue1.id, status=Status.CLOSED)
        core.issues.update(issue2.id, status=Status.CLOSED)

        # Archive all closed issues
        from click.testing import CliRunner

        from roadmap.adapters.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["issue", "archive", "--all-closed", "--force"])
        assert result.exit_code == 0, f"Archive all-closed failed: {result.output}"

        # Check that no issue ID appears in both directories
        active_ids = self.get_active_issue_ids(core)
        archived_ids = self.get_archived_issue_ids(core)

        overlap = active_ids & archived_ids
        assert not overlap, f"Issues found in both active and archive: {overlap}"

        # Verify issue3 is still active, issue1 and issue2 are archived
        assert issue3.id[:8] in active_ids, "Active open issue should still be active"
        assert issue1.id[:8] not in active_ids, "Closed issue1 should not be active"
        assert issue2.id[:8] not in active_ids, "Closed issue2 should not be active"
        assert issue1.id[:8] in archived_ids, "Closed issue1 should be archived"
        assert issue2.id[:8] in archived_ids, "Closed issue2 should be archived"

    def test_archive_handles_existing_archive_file(self, core):
        """Ensure archive operation skips if file already exists in archive."""
        issue = core.issues.create("Test Issue", priority=Priority.MEDIUM)
        core.issues.update(issue.id, status=Status.CLOSED)

        from click.testing import CliRunner

        from roadmap.adapters.cli import main

        runner = CliRunner()

        # Archive once
        result = runner.invoke(main, ["issue", "archive", issue.id, "--force"])
        assert result.exit_code == 0, f"First archive failed: {result.output}"

        active_after_first = self.count_active_issue_files(core)
        archived_after_first = self.count_archived_issue_files(core)

        # Try to archive again (should skip since already archived)
        result = runner.invoke(main, ["issue", "archive", issue.id, "--force"])
        # This should either succeed with 0 archived or show a warning
        assert result.exit_code == 0, f"Second archive should not fail: {result.output}"

        # Verify no new files were created
        active_after_second = self.count_active_issue_files(core)
        archived_after_second = self.count_archived_issue_files(core)

        assert (
            active_after_second == active_after_first
        ), "Active files should not change on second archive"
        assert (
            archived_after_second == archived_after_first
        ), "Archived files should not change on second archive"

        # Most importantly: verify no duplicates exist
        active_ids = self.get_active_issue_ids(core)
        archived_ids = self.get_archived_issue_ids(core)
        overlap = active_ids & archived_ids
        assert not overlap, f"No duplicates should exist: {overlap}"
