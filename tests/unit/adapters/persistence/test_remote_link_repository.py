"""Wave 2 tests for RemoteLinkRepository."""

from __future__ import annotations

from roadmap.adapters.persistence.database_manager import DatabaseManager
from roadmap.adapters.persistence.repositories.remote_link_repository import (
    RemoteLinkRepository,
)


def _repo(tmp_path):
    db = DatabaseManager(tmp_path / "remote_links.db")
    return db, RemoteLinkRepository(db._get_connection, db.transaction)


def _seed_issue(db: DatabaseManager, issue_id: str) -> None:
    with db.transaction() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO issues (id, title, status, priority, issue_type)
            VALUES (?, ?, 'open', 'medium', 'task')
            """,
            (issue_id, f"Issue {issue_id}"),
        )


def test_link_get_validate_and_unlink_roundtrip(tmp_path) -> None:
    db, repo = _repo(tmp_path)
    _seed_issue(db, "issue-1")

    assert repo.link_issue("issue-1", "github", 101) is True
    assert repo.get_remote_id("issue-1", "github") == 101
    assert repo.validate_link("issue-1", "github", "101") is True
    assert repo.validate_link("issue-1", "github", "999") is False

    assert repo.unlink_issue("issue-1", "github") is True
    assert repo.get_remote_id("issue-1", "github") is None


def test_get_issue_uuid_and_backend_and_issue_views(tmp_path) -> None:
    db, repo = _repo(tmp_path)
    _seed_issue(db, "issue-1")
    _seed_issue(db, "issue-2")
    repo.link_issue("issue-1", "github", 55)
    repo.link_issue("issue-1", "gitlab", "abc")
    repo.link_issue("issue-2", "github", "77")

    assert repo.get_issue_uuid("github", 55) == "issue-1"
    assert repo.get_issue_uuid("github", 999) is None

    issue_links = repo.get_all_links_for_issue("issue-1")
    assert issue_links["github"] == 55
    assert issue_links["gitlab"] == "abc"

    backend_links = repo.get_all_links_for_backend("github")
    assert backend_links["issue-1"] == 55
    assert backend_links["issue-2"] == 77


def test_bulk_import_and_clear_all(tmp_path) -> None:
    db, repo = _repo(tmp_path)
    _seed_issue(db, "issue-1")
    _seed_issue(db, "issue-2")
    _seed_issue(db, "issue-3")

    imported = repo.bulk_import_from_yaml(
        {
            "issue-1": {"github": 1, "gitlab": "A"},
            "issue-2": {"github": 2},
            "issue-3": {},
        }
    )

    assert imported == 3
    assert repo.get_remote_id("issue-1", "github") == 1
    assert repo.get_remote_id("issue-2", "github") == 2

    assert repo.clear_all() is True
    assert repo.get_all_links_for_backend("github") == {}
