"""Tests for orphaned issues fixer behavior."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.health.fixers.orphaned_issues_fixer import OrphanedIssuesFixer


@contextmanager
def chdir(path: Path):
    """Temporarily change working directory."""
    import os

    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def test_scan_reports_found_count_and_details(tmp_path):
    """Scan should summarize misplaced issues with id/title details."""
    core = MagicMock()
    fixer = OrphanedIssuesFixer(core)

    with patch.object(
        fixer,
        "_find_misplaced_issues",
        return_value=[
            {"id": "i1", "title": "One", "target_folder": "x"},
            {"id": "i2", "title": "Two", "target_folder": "y"},
        ],
    ):
        result = fixer.scan()

    assert result["found"] is True
    assert result["count"] == 2
    assert result["details"] == [
        {"id": "i1", "title": "One"},
        {"id": "i2", "title": "Two"},
    ]


def test_find_misplaced_returns_empty_when_issues_dir_missing(tmp_path):
    """Finder should return empty list when roadmap issues directory is absent."""
    core = MagicMock()
    core.issues.list.return_value = []
    fixer = OrphanedIssuesFixer(core)

    with chdir(tmp_path):
        assert fixer._find_misplaced_issues() == []


def test_apply_moves_loose_file_to_existing_target_folder(tmp_path):
    """Apply should move a loose issue file into resolved milestone folder."""
    core = MagicMock()
    fixer = OrphanedIssuesFixer(core)

    issues_root = tmp_path / ".roadmap" / "issues"
    issues_root.mkdir(parents=True)
    loose_file = issues_root / "i1_test.md"
    loose_file.write_text("body")

    target = issues_root / "m1"
    target.mkdir(parents=True)

    with (
        chdir(tmp_path),
        patch.object(
            fixer,
            "_find_misplaced_issues",
            return_value=[
                {
                    "id": "i1",
                    "title": "Issue 1",
                    "current_folder": str(issues_root),
                    "target_folder": str(target),
                }
            ],
        ),
    ):
        result = fixer.apply()

    assert result.success is True
    assert result.changes_made == 1
    assert (target / "i1_test.md").exists()


def test_apply_falls_back_to_backlog_when_target_missing(tmp_path):
    """When target folder missing, apply should move to backlog folder."""
    core = MagicMock()
    fixer = OrphanedIssuesFixer(core)

    issues_root = tmp_path / ".roadmap" / "issues"
    current = issues_root / "wrong"
    current.mkdir(parents=True)
    file_path = current / "i2_work.md"
    file_path.write_text("body")

    missing_target = issues_root / "does-not-exist"

    with (
        chdir(tmp_path),
        patch.object(
            fixer,
            "_find_misplaced_issues",
            return_value=[
                {
                    "id": "i2",
                    "title": "Issue 2",
                    "current_folder": str(current),
                    "target_folder": str(missing_target),
                }
            ],
        ),
    ):
        result = fixer.apply()

    backlog_file = tmp_path / ".roadmap" / "issues" / "backlog" / "i2_work.md"
    assert result.success is True
    assert result.changes_made == 1
    assert backlog_file.exists()


def test_apply_records_failed_item_when_move_raises(tmp_path):
    """Move errors should mark fixer result unsuccessful with zero changes."""
    core = MagicMock()
    fixer = OrphanedIssuesFixer(core)

    issues_root = tmp_path / ".roadmap" / "issues"
    issues_root.mkdir(parents=True)
    (issues_root / "i3_note.md").write_text("body")

    target = issues_root / "m2"

    with (
        chdir(tmp_path),
        patch.object(
            fixer,
            "_find_misplaced_issues",
            return_value=[
                {
                    "id": "i3",
                    "title": "Issue 3",
                    "current_folder": str(issues_root),
                    "target_folder": str(target),
                }
            ],
        ),
        patch(
            "roadmap.adapters.cli.health.fixers.orphaned_issues_fixer.shutil.move",
            side_effect=OSError("deny"),
        ),
    ):
        result = fixer.apply()

    assert result.success is False
    assert result.changes_made == 0
    assert result.items_count == 1
    assert result.affected_items == []


def test_find_issue_folder_prefers_root_for_loose_files(tmp_path):
    """Loose files in issues root should return the root folder."""
    core = MagicMock()
    fixer = OrphanedIssuesFixer(core)

    issues_dir = tmp_path / ".roadmap" / "issues"
    archive_dir = tmp_path / ".roadmap" / "archive" / "issues"
    issues_dir.mkdir(parents=True)
    archive_dir.mkdir(parents=True)
    (issues_dir / "abc_loose.md").write_text("body")

    folder = fixer._find_issue_folder("abc", issues_dir, archive_dir)
    assert folder == issues_dir
