"""Failed derived-state maintenance must preserve canonical bytes and allow retry."""

import errno
import os
import sqlite3

import pytest

from roadmap.adapters.outbound.persistence.projection import (
    ProjectionError,
    SQLiteProjection,
)
from tests.unit.adapters.persistence.test_canonical_persistence import _canonical_set


@pytest.mark.parametrize("stage", ["insert", "replace"])
@pytest.mark.parametrize("error_number", [errno.ENOSPC, errno.EACCES])
def test_failed_projection_rebuild_preserves_existing_index_and_canonical_data(
    tmp_path, monkeypatch, stage, error_number
):
    repository, canonical = _canonical_set(tmp_path)
    projection = SQLiteProjection(
        repository.roadmap_dir / "db/projection.db", repository
    )
    projection.rebuild()
    previous = projection.path.read_bytes()

    def fail(*_args):
        raise OSError(error_number, os.strerror(error_number))

    with monkeypatch.context() as patch:
        if stage == "insert":
            patch.setattr(projection, "_insert", fail)
        else:
            patch.setattr(os, "replace", fail)
        with pytest.raises(OSError) as caught:
            projection.rebuild()
        assert caught.value.errno == error_number

    assert projection.path.read_bytes() == previous
    assert projection.stale_path.exists()
    assert not list(projection.path.parent.glob(".projection.db.*"))
    assert {path: path.read_bytes() for path in canonical} == canonical
    projection.rebuild()
    assert not projection.stale_path.exists()
    assert len(projection.query()) == 3
    assert {path: path.read_bytes() for path in canonical} == canonical


def test_partial_projection_refresh_rolls_back_and_retry_reads_latest_documents(
    tmp_path, monkeypatch
):
    repository, canonical = _canonical_set(tmp_path)
    projection = SQLiteProjection(
        repository.roadmap_dir / "db/projection.db", repository
    )
    projection.rebuild()
    original = projection.path.read_bytes()
    issue = next(path for path in canonical if path.name == "issue-1.md")
    issue.write_text(issue.read_text().replace("A useful issue", "Latest manual edit"))
    latest = {path: path.read_bytes() for path in canonical}

    def fail(*_args):
        raise sqlite3.OperationalError("injected failure after deleting old index row")

    with monkeypatch.context() as patch:
        patch.setattr(projection, "_insert", fail)
        with pytest.raises(ProjectionError, match="injected failure"):
            projection.ensure_current()

    assert projection.path.read_bytes() == original
    assert projection.stale_path.exists()
    assert {path: path.read_bytes() for path in canonical} == latest
    assert projection.ensure_current() == "rebuilt"
    assert (
        next(row for row in projection.query("issue"))["name"] == "Latest manual edit"
    )
    assert {path: path.read_bytes() for path in canonical} == latest
