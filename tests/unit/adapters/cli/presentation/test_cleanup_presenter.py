"""Tests for cleanup presenter output branches."""

from pathlib import Path

from roadmap.adapters.cli.presentation.cleanup_presenter import CleanupPresenter
from roadmap.core.services.health.backup_cleanup_service import BackupCleanupResult
from roadmap.core.services.health.file_repair_service import FileRepairResult


def test_present_folder_issues_misplaced_only(capsys):
    """Presenter should render misplaced section when orphaned is absent."""
    presenter = CleanupPresenter()

    presenter.present_folder_issues(
        {
            "misplaced": [
                {
                    "issue_id": "iss-1",
                    "title": "Move me",
                    "current_location": ".roadmap/issues",
                    "expected_location": ".roadmap/issues/backlog",
                }
            ]
        }
    )

    out = capsys.readouterr().out
    assert "Found 1 issue(s) in wrong folders" in out
    assert "iss-1: Move me" in out
    assert "Current:" in out
    assert "Expected:" in out
    assert "orphaned issue" not in out.lower()


def test_present_folder_issues_orphaned_only(capsys):
    """Presenter should render orphaned section independently."""
    presenter = CleanupPresenter()

    presenter.present_folder_issues(
        {
            "orphaned": [
                {
                    "issue_id": "iss-2",
                    "title": "Orphan",
                    "location": ".roadmap/issues/missing",
                }
            ]
        }
    )

    out = capsys.readouterr().out
    assert "Found 1 orphaned issue(s)" in out
    assert "iss-2: Orphan" in out
    assert "Location:" in out


def test_present_backup_cleanup_result_with_failures(capsys):
    """Presenter should show both success and warning lines."""
    presenter = CleanupPresenter()
    result = BackupCleanupResult()
    result.add_deleted(Path("a.md"), 1024 * 1024)
    result.add_failed(Path("b.md"), "permission denied")

    presenter.present_backup_cleanup_result(result)

    out = capsys.readouterr().out
    assert "Cleaned up 1 backup file(s)" in out
    assert "1 file(s) failed to delete" in out


def test_present_malformed_repair_result_fixed_and_errors(capsys):
    """Presenter should display fixed files and error files in one run."""
    presenter = CleanupPresenter()
    result = FileRepairResult()
    result.add_fixed("issues/a.md")
    result.add_error("issues/b.md")

    presenter.present_malformed_repair_result(result)

    out = capsys.readouterr().out
    assert "Fixed 1 file(s)" in out
    assert "Could not fix 1 file(s)" in out
    assert "issues/a.md" in out
    assert "issues/b.md" in out


def test_present_duplicate_resolution_keeps_latest_file(tmp_path, capsys):
    """Presenter should report newest file as keeper based on mtime."""
    presenter = CleanupPresenter()
    roadmap_dir = tmp_path
    issue_dir = roadmap_dir / ".roadmap" / "issues"
    issue_dir.mkdir(parents=True)

    old_file = issue_dir / "iss-7_old.md"
    new_file = issue_dir / "iss-7_new.md"
    old_file.write_text("old")
    new_file.write_text("new")

    old_file.touch()
    new_file.touch()

    presenter.present_duplicate_resolution({"iss-7": [old_file, new_file]}, roadmap_dir)

    out = capsys.readouterr().out
    assert "Resolving 1 duplicate issue(s)" in out
    assert "Issue ID: iss-7" in out
    assert "Keeping:" in out
    assert "Removing:" in out
    assert "iss-7_new.md" in out
