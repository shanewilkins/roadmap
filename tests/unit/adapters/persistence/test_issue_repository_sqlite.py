"""Focused tests for SQL IssueRepository behavior."""

import sqlite3
from contextlib import contextmanager

import pytest

from roadmap.adapters.persistence.repositories.issue_repository import IssueRepository


@contextmanager
def _transaction(conn):
    """Simple transaction wrapper matching repository contract."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


@pytest.fixture
def repository():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE milestones (id TEXT PRIMARY KEY)")
    conn.execute(
        """
        CREATE TABLE issues (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            milestone_id TEXT,
            title TEXT,
            headline TEXT,
            description TEXT,
            status TEXT,
            priority TEXT,
            issue_type TEXT,
            assignee TEXT,
            estimate_hours REAL,
            due_date TEXT,
            metadata TEXT,
            archived INTEGER DEFAULT 0,
            archived_at TEXT
        )
        """
    )
    yield conn, IssueRepository(lambda: conn, lambda: _transaction(conn))
    conn.close()


def test_create_missing_project_and_milestone_are_set_to_none(repository):
    """Unknown project/milestone IDs should be normalized to NULL."""
    conn, repo = repository

    issue_id = repo.create(
        {
            "id": "iss-1",
            "project_id": "proj-missing",
            "milestone_id": "mile-missing",
            "title": "T",
            "description": "D",
        }
    )

    row = conn.execute(
        "SELECT project_id, milestone_id FROM issues WHERE id = ?", (issue_id,)
    ).fetchone()
    assert row is not None
    assert row["project_id"] is None
    assert row["milestone_id"] is None


def test_update_empty_dict_returns_false_without_query_changes(repository):
    """Empty update payload should return False and not modify row."""
    conn, repo = repository
    repo.create({"id": "iss-2", "title": "T", "description": "D"})

    result = repo.update("iss-2", {})

    assert result is False
    count = conn.execute("SELECT COUNT(*) FROM issues WHERE id = 'iss-2'").fetchone()[0]
    assert count == 1


def test_delete_many_empty_list_returns_zero(repository):
    """Batch delete should short-circuit when no IDs are provided."""
    _conn, repo = repository
    assert repo.delete_many([]) == 0


def test_mark_archived_true_sets_flag_and_timestamp(repository):
    """Archiving should set archived=1 and archived_at timestamp."""
    conn, repo = repository
    repo.create({"id": "iss-3", "title": "T", "description": "D"})

    assert repo.mark_archived("iss-3", archived=True) is True

    row = conn.execute(
        "SELECT archived, archived_at FROM issues WHERE id = 'iss-3'"
    ).fetchone()
    assert row is not None
    assert row["archived"] == 1
    assert row["archived_at"] is not None


def test_mark_archived_false_clears_timestamp(repository):
    """Unarchiving should clear archived_at and set archived=0."""
    conn, repo = repository
    repo.create({"id": "iss-4", "title": "T", "description": "D"})
    assert repo.mark_archived("iss-4", archived=True) is True

    assert repo.mark_archived("iss-4", archived=False) is True

    row = conn.execute(
        "SELECT archived, archived_at FROM issues WHERE id = 'iss-4'"
    ).fetchone()
    assert row is not None
    assert row["archived"] == 0
    assert row["archived_at"] is None
