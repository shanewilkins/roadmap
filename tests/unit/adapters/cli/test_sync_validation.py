"""Wave 3 tests for sync validation CLI behavior."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from click.testing import CliRunner

from roadmap.adapters.cli.sync_validation import _apply_auto_fix, validate_links
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


def test_validate_links_exits_when_issues_dir_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    core = SimpleNamespace(
        is_initialized=lambda: True,
        issues_dir=tmp_path / "missing-issues",
    )

    result = runner.invoke(validate_links, [], obj={"core": core})

    assert result.exit_code == 1
    output = clean_cli_output(result.output)
    assert "Issues directory not found" in output


def test_validate_links_reports_no_issue_files(tmp_path: Path) -> None:
    runner = CliRunner()
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)

    validation = SimpleNamespace(
        collect_remote_link_validation_data=lambda _d: {
            "issue_files": [],
            "yaml_remote_ids": {},
            "unparseable_files": [],
            "db_links": {},
        },
        build_remote_link_report=lambda _yaml, _db: {
            "files_with_remote_ids": 0,
            "database_links": 0,
            "discrepancies": [],
            "missing_in_db": [],
            "extra_in_db": [],
            "duplicate_remote_ids": {},
        },
    )
    core = SimpleNamespace(
        is_initialized=lambda: True,
        issues_dir=issues_dir,
        validation=validation,
    )

    result = runner.invoke(validate_links, [], obj={"core": core})

    assert result.exit_code == 0
    output = clean_cli_output(result.output)
    assert "No issue files found" in output


def test_apply_auto_fix_calls_validation_and_reports_counts() -> None:
    console = Mock()
    core = SimpleNamespace(
        validation=SimpleNamespace(
            apply_remote_link_fixes=lambda *_args, **_kwargs: {
                "fixed_count": 2,
                "removed_count": 1,
                "deduped_count": 1,
            }
        )
    )

    _apply_auto_fix(
        core=core,
        yaml_remote_ids={"id-1": {"github": 101}},
        validation_report={
            "missing_in_db": ["id-1"],
            "extra_in_db": ["id-2"],
            "duplicate_remote_ids": {"github:101": ["id-1", "id-3"]},
        },
        console=console,
        dry_run=False,
        verbose=True,
        prune_extra=True,
        dedupe=True,
    )

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Fixed 2 missing remote links" in rendered
    assert "Removed 1 extra remote links" in rendered
    assert "Removed 1 duplicate remote links" in rendered
