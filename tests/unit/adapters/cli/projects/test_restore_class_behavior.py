"""Focused behavior tests for ProjectRestore class implementation."""

from unittest.mock import Mock, patch

from roadmap.adapters.cli.projects.restore_class import ProjectRestore


def test_get_archived_files_to_restore_returns_empty_when_archive_missing():
    """Missing archive directory should produce an empty restore list."""
    restore = ProjectRestore(core=Mock(), console=Mock())

    archive_dir = Mock()
    archive_dir.exists.return_value = False

    with patch(
        "roadmap.adapters.cli.crud.crud_helpers.get_archive_dir",
        return_value=archive_dir,
    ):
        result = restore.get_archived_files_to_restore()

    assert result == []


def test_get_archived_files_to_restore_filters_by_entity_prefix(tmp_path):
    """Entity restore should match first 8 chars of ID prefix in archived files."""
    restore = ProjectRestore(core=Mock(), console=Mock())

    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    wanted = archive_dir / "12345678-project.md"
    wanted.write_text("project")
    (archive_dir / "87654321-project.md").write_text("other")

    with patch(
        "roadmap.adapters.cli.crud.crud_helpers.get_archive_dir",
        return_value=archive_dir,
    ):
        result = restore.get_archived_files_to_restore(entity_id="12345678-abcdef")

    assert result == [wanted]


def test_get_archived_files_to_restore_returns_all_markdown_files(tmp_path):
    """Without entity id, class should restore all archived project markdown files."""
    restore = ProjectRestore(core=Mock(), console=Mock())

    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    first = archive_dir / "a.md"
    second = archive_dir / "b.md"
    first.write_text("a")
    second.write_text("b")

    with patch(
        "roadmap.adapters.cli.crud.crud_helpers.get_archive_dir",
        return_value=archive_dir,
    ):
        result = restore.get_archived_files_to_restore()

    assert sorted(result) == [first, second]


def test_post_restore_hook_marks_projects_unarchived_for_each_file(tmp_path):
    """post_restore_hook should update DB archive state for every restored file."""
    core = Mock()
    restore = ProjectRestore(core=core, console=Mock())

    restored_files = [
        tmp_path / "12345678-sample.md",
        tmp_path / "abcdef12-another.md",
    ]

    restore.post_restore_hook(restored_files)

    assert core.db.mark_project_archived.call_count == 2
    core.db.mark_project_archived.assert_any_call("12345678", archived=False)
    core.db.mark_project_archived.assert_any_call("abcdef12", archived=False)


def test_post_restore_hook_prints_warning_when_db_update_fails(tmp_path):
    """DB update failures should emit warning and continue remaining files."""
    core = Mock()
    core.db.mark_project_archived.side_effect = RuntimeError("db down")
    console = Mock()
    restore = ProjectRestore(core=core, console=console)

    restore.post_restore_hook([tmp_path / "12345678-sample.md"])

    printed = "\n".join(str(call) for call in console.print.call_args_list)
    assert "Failed to update restoration status" in printed
