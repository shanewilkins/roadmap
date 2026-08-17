"""Phase 6 canonical/projection issue-query adapter tests."""

from datetime import UTC, datetime

import pytest
import yaml

from roadmap.adapters.outbound.persistence.documents import (
    DocumentError,
    DocumentRepository,
)
from roadmap.adapters.outbound.persistence.issue_queries import DocumentIssueQueries
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.domain.types import EntityId


def _write_issue(root, identity="issue-1", title="Café ☕"):
    path = root / "issues/backlog" / f"{identity}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    values = {
        "id": identity,
        "title": title,
        "status": "todo",
        "priority": "medium",
        "issue_type": "feature",
        "created": datetime(2026, 8, 17, tzinfo=UTC).isoformat(),
        "updated": datetime(2026, 8, 17, tzinfo=UTC).isoformat(),
        "comments": [
            {
                "id": 1,
                "author": "author",
                "body": "Comment",
                "created_at": datetime(2026, 8, 17, tzinfo=UTC).isoformat(),
                "updated_at": datetime(2026, 8, 17, tzinfo=UTC).isoformat(),
            }
        ],
    }
    frontmatter = yaml.safe_dump(values, sort_keys=False, allow_unicode=True).rstrip()
    path.write_text(f"---\n{frontmatter}\n---\n\nBody\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("projection_state", ["absent", "healthy", "corrupt"])
def test_query_results_are_identical_for_projection_states(tmp_path, projection_state):
    root = tmp_path / ".roadmap"
    _write_issue(root)
    repository = DocumentRepository(root)
    projection = SQLiteProjection(root / "db/projection.db", repository)
    if projection_state == "healthy":
        projection.rebuild()
    elif projection_state == "corrupt":
        projection.path.parent.mkdir(parents=True)
        projection.path.write_bytes(b"broken")

    records = DocumentIssueQueries(repository, projection).list_issue_records()

    assert [record.issue.id for record in records] == ["issue-1"]
    assert records[0].comments[0].body == "Comment"
    assert (
        DocumentIssueQueries(repository).load_issue_record(EntityId("issue-1"))
        == records[0]
    )


def test_projection_candidate_ids_are_verified_against_canonical_files(tmp_path):
    root = tmp_path / ".roadmap"
    path = _write_issue(root, title="Before")
    repository = DocumentRepository(root)
    projection = SQLiteProjection(root / "db/projection.db", repository)
    projection.rebuild()
    path.write_text(path.read_text().replace("Before", "Canonical wins"))

    record = DocumentIssueQueries(repository, projection).list_issue_records()[0]

    assert record.issue.title == "Canonical wins"


def test_malformed_issue_fails_instead_of_returning_projection_data(tmp_path):
    root = tmp_path / ".roadmap"
    path = _write_issue(root)
    repository = DocumentRepository(root)
    projection = SQLiteProjection(root / "db/projection.db", repository)
    projection.rebuild()
    path.write_text("not a canonical document")

    with pytest.raises(DocumentError, match="frontmatter"):
        DocumentIssueQueries(repository, projection).list_issue_records()
