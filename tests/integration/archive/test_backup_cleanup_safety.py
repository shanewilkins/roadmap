"""Populated backup cleanup must delete exactly the selected legacy files."""

import os
from datetime import UTC, datetime, timedelta

import pytest

from roadmap.adapters.inbound.cli.cleanup import _candidates
from roadmap.bootstrap import cli
from tests.fixtures.ansi import clean_cli_output

NOW = datetime(2026, 10, 6, tzinfo=UTC)


def backup(root, name, age=0):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"Backup {name}\n")
    instant = (NOW - timedelta(days=age)).timestamp()
    os.utime(path, (instant, instant))
    return path


@pytest.mark.parametrize(
    "keep,days,expected",
    [
        (1, None, {"alpha_b.backup.md", "alpha_c.backup.md"}),
        (10, 30, {"alpha_c.backup.md"}),
        (1, 30, {"alpha_b.backup.md", "alpha_c.backup.md"}),
        (
            0,
            None,
            {
                "alpha_a.backup.md",
                "alpha_b.backup.md",
                "alpha_c.backup.md",
                "beta_a.backup.md",
            },
        ),
    ],
)
def test_retention_selection_respects_groups_age_boundary_and_ties(
    tmp_path, keep, days, expected
):
    # Equal timestamps sort by filename. Exactly 30 days old is retained by
    # the age criterion; more than 30 days old is selected.
    for name, age in [
        ("alpha_a.backup.md", 30),
        ("alpha_b.backup.md", 30),
        ("alpha_c.backup.md", 31),
        ("beta_a.backup.md", 0),
    ]:
        backup(tmp_path, name, age)
    backup(tmp_path, "canonical.md", 90)
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    assert {p.name for p in _candidates(tmp_path, keep, days, NOW)} == expected
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.fixture
def populated(tmp_path, monkeypatch, cli_runner):
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(cli, ["init", "--skip-project", "--non-interactive"])
    assert result.exit_code == 0, result.output
    root = tmp_path / ".roadmap"
    backup(root / "backups", "issue_a.backup.md")
    backup(root / "backups", "issue_b.backup.md", 1)
    backup(root / "backups", "untouched.txt")
    backup(root / "artifacts", "protected.md")
    return root


@pytest.mark.parametrize(
    "arguments,input_text",
    [
        (["--dry-run"], None),
        ([], "n\n"),
        (["--keep", "-1"], None),
        (["--days", "-1"], None),
    ],
)
def test_preview_decline_and_invalid_options_preserve_all_files(
    populated, cli_runner, arguments, input_text
):
    before = {p: p.read_bytes() for p in populated.rglob("*") if p.is_file()}
    result = cli_runner.invoke(
        cli, ["cleanup", "--keep", "1", *arguments], input=input_text
    )
    assert result.exit_code == (
        0 if "--dry-run" in arguments else 2 if "-1" in arguments else 1
    ), result.output
    assert {p: p.read_bytes() for p in populated.rglob("*") if p.is_file()} == before


def test_confirmed_cleanup_only_removes_listed_backup(populated, cli_runner):
    before = {p: p.read_bytes() for p in populated.rglob("*") if p.is_file()}
    result = cli_runner.invoke(cli, ["cleanup", "--keep", "1"], input="y\n")
    assert result.exit_code == 0, result.output
    removed = populated / "backups/issue_b.backup.md"
    output = clean_cli_output(result.output)
    assert "backups/issue_b.backup.md" in output
    assert "Removed 1 backup file(s)" in output
    assert not removed.exists()
    assert {p: p.read_bytes() for p in populated.rglob("*") if p.is_file()} == {
        p: b for p, b in before.items() if p != removed
    }


def test_partial_cleanup_failure_returns_nonzero_and_names_failed_file(
    populated, cli_runner, monkeypatch
):
    denied = populated / "backups/issue_b.backup.md"
    original = os.unlink

    def unlink(path, *args, **kwargs):
        if path == denied.name and kwargs.get("dir_fd") is not None:
            raise PermissionError("injected denial")
        return original(path, *args, **kwargs)

    before = denied.read_bytes()
    monkeypatch.setattr(os, "unlink", unlink)
    result = cli_runner.invoke(cli, ["cleanup", "--keep", "0", "--force"])
    assert result.exit_code == 1, result.output
    output = clean_cli_output(result.output)
    assert "incomplete" in output
    assert "backups/issue_b.backup.md" in output
    assert "Removed 2" not in output
    assert not (populated / "backups/issue_a.backup.md").exists()
    assert denied.read_bytes() == before
    assert (populated / "artifacts/protected.md").exists()


@pytest.mark.parametrize("dry_run", [True, False])
@pytest.mark.parametrize("linked", ["directory", "file", "dangling-file"])
def test_cleanup_refuses_symlink_scope_and_preserves_external_files(
    populated, cli_runner, tmp_path, dry_run, linked
):
    outside = tmp_path / "outside"
    external = backup(outside, "external.backup.md")
    if linked == "directory":
        (populated / "backups").rename(populated / "original-backups")
        (populated / "backups").symlink_to(outside, target_is_directory=True)
    else:
        target = external if linked == "file" else outside / "missing.md"
        (populated / "backups/link.backup.md").symlink_to(target)
    before = {p: p.read_bytes() for p in populated.rglob("*") if p.is_file()}
    result = cli_runner.invoke(
        cli, ["cleanup", "--keep", "0", "--dry-run" if dry_run else "--force"]
    )
    assert result.exit_code == 1, result.output
    assert "Unsafe backup path" in clean_cli_output(result.output)
    assert external.read_text() == "Backup external.backup.md\n"
    assert {p: p.read_bytes() for p in populated.rglob("*") if p.is_file()} == before


def test_cleanup_rechecks_directory_after_confirmation(
    populated, cli_runner, monkeypatch, tmp_path
):
    import click

    outside = tmp_path / "outside"
    external = backup(outside, "issue_a.backup.md")

    def confirm(*_args, **_kwargs):
        (populated / "backups").rename(populated / "original-backups")
        (populated / "backups").symlink_to(outside, target_is_directory=True)
        return True

    monkeypatch.setattr(click, "confirm", confirm)
    result = cli_runner.invoke(cli, ["cleanup", "--keep", "0"])
    assert result.exit_code == 1, result.output
    assert external.read_text() == "Backup issue_a.backup.md\n"
    assert len(tuple((populated / "original-backups").glob("*.backup.md"))) == 2


def test_directory_swap_between_validation_and_open_cannot_delete_external_backup(
    populated, cli_runner, monkeypatch, tmp_path
):
    outside = tmp_path / "outside"
    external = backup(outside, "issue_b.backup.md")
    original = os.open
    swapped = False

    def open_directory(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == populated / "backups" and not swapped:
            swapped = True
            path.rename(populated / "original-backups")
            path.symlink_to(outside, target_is_directory=True)
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", open_directory)
    result = cli_runner.invoke(cli, ["cleanup", "--keep", "1", "--force"])
    assert result.exit_code == 1, result.output
    assert "incomplete" in clean_cli_output(result.output)
    assert external.read_text() == "Backup issue_b.backup.md\n"
    assert len(tuple((populated / "original-backups").glob("*.backup.md"))) == 2
