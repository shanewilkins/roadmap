"""Tests for local Git conflict inspection."""

from pathlib import Path

from roadmap.adapters.persistence.storage.conflicts import ConflictService


def test_missing_roadmap_directory_has_no_conflicts(tmp_path: Path) -> None:
    service = ConflictService()

    assert service.check_git_conflicts(tmp_path / "missing") == []


def test_detects_conflict_markers_in_canonical_documents(
    tmp_path: Path, monkeypatch
) -> None:
    roadmap_dir = tmp_path / ".roadmap"
    issue_dir = roadmap_dir / "issues"
    issue_dir.mkdir(parents=True)
    issue_file = issue_dir / "conflicted.md"
    issue_file.write_text("<<<<<<< HEAD\nlocal\n=======\nother\n>>>>>>> branch\n")
    monkeypatch.chdir(tmp_path)

    conflicts = ConflictService().check_git_conflicts(roadmap_dir)

    assert conflicts == [".roadmap/issues/conflicted.md"]


def test_clean_canonical_documents_have_no_conflicts(tmp_path: Path) -> None:
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir()
    (roadmap_dir / "project.md").write_text("---\nname: local\n---\n")

    assert ConflictService().check_git_conflicts(roadmap_dir) == []


def test_unreadable_file_is_skipped(tmp_path: Path, monkeypatch) -> None:
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir()
    issue_file = roadmap_dir / "issue.md"
    issue_file.write_text("clean")

    def fail_read_text(*args, **kwargs):
        raise OSError("cannot read")

    monkeypatch.setattr("builtins.open", fail_read_text)

    assert ConflictService().check_git_conflicts(roadmap_dir) == []
