"""Unit tests for db_integrity helpers."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from roadmap.adapters.cli.health.db_integrity import (
    _build_report,
    _collect_local_issue_ids,
    _load_db_state,
    _print_plain_report,
)


@pytest.mark.parametrize(
    "files,parse_error_names",
    [
        (["a.md", "b.md"], []),
        (["ok.md", "bad.md"], ["bad.md"]),
    ],
)
def test_collect_local_issue_ids(tmp_path, files, parse_error_names, monkeypatch):
    """Collector should return parsed IDs and retain parse errors."""
    issues_dir = tmp_path / "issues"
    issues_dir.mkdir()

    for name in files:
        (issues_dir / name).write_text("# test")

    def fake_parse(file_path: Path):
        if file_path.name in parse_error_names:
            raise ValueError("parse failed")
        return SimpleNamespace(id=f"id-{file_path.stem}")

    monkeypatch.setattr(
        "roadmap.adapters.cli.health.db_integrity.IssueParser.parse_issue_file",
        fake_parse,
    )

    local_ids, parse_errors = _collect_local_issue_ids(issues_dir)

    assert all(item.startswith("id-") for item in local_ids)
    assert len(parse_errors) == len(parse_error_names)


def test_load_db_state_reads_expected_tables(tmp_path):
    """Database loader should return IDs from all integrity tables."""
    import sqlite3

    db_path = tmp_path / "state.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE issues (id TEXT)")
    conn.execute("CREATE TABLE sync_base_state (issue_id TEXT)")
    conn.execute("CREATE TABLE issue_remote_links (issue_id TEXT, remote_id TEXT)")

    conn.executemany("INSERT INTO issues (id) VALUES (?)", [("A",), ("B",)])
    conn.executemany("INSERT INTO sync_base_state (issue_id) VALUES (?)", [("A",)])
    conn.executemany(
        "INSERT INTO issue_remote_links (issue_id, remote_id) VALUES (?, ?)",
        [("A", "1"), ("B", "2")],
    )
    conn.commit()
    conn.close()

    db_ids, baseline_ids, remote_links_count = _load_db_state(db_path)  # type: ignore[misc]

    assert db_ids == {"A", "B"}
    assert baseline_ids == {"A"}
    assert remote_links_count == 2


def test_build_report_computes_discrepancy_counts_and_ids():
    """Report builder should compute directional set differences correctly."""
    report = _build_report(
        local_ids={"A", "B"},
        db_ids={"B", "C"},
        baseline_ids={"C", "D"},
        remote_links_count=5,
        parse_errors=[("file.md", "err")],
    )

    assert report["missing_in_db"] == 1
    assert report["extra_in_db"] == 1
    assert report["baseline_missing_issue"] == 1
    assert report["issue_missing_baseline"] == 1
    assert report["missing_in_db_ids"] == ["A"]
    assert report["extra_in_db_ids"] == ["C"]


def test_print_plain_report_shows_ids_when_requested(capsys):
    """Plain report renderer should include IDs and parse error details."""
    report = {
        "local_issue_files": 2,
        "db_issues": 1,
        "sync_base_state": 1,
        "remote_links": 0,
        "missing_in_db": 1,
        "extra_in_db": 0,
        "baseline_missing_issue": 0,
        "issue_missing_baseline": 0,
        "missing_in_db_ids": ["A"],
        "extra_in_db_ids": [],
        "baseline_missing_issue_ids": [],
        "issue_missing_baseline_ids": [],
        "parse_errors": [("x.md", "bad")],
    }

    _print_plain_report(report, show_ids=True, limit=5)
    out = capsys.readouterr().out

    assert "DB Integrity Report" in out
    assert "missing_in_db_ids:" in out
    assert "A" in out
    assert "x.md: bad" in out
