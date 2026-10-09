"""Real SQLite handles must close before projection operations return or raise."""

import gc
import sqlite3

import pytest

from roadmap.adapters.outbound.persistence.projection import (
    ProjectionError,
    SQLiteProjection,
)
from tests.unit.adapters.persistence.test_canonical_persistence import _canonical_set


@pytest.fixture
def connections(monkeypatch):
    opened = []
    connect = sqlite3.connect

    class TrackedConnection(sqlite3.Connection):
        close_calls = 0

        def close(self):
            self.close_calls += 1
            super().close()

    def track(path):
        connection = connect(path, factory=TrackedConnection)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", track)
    yield opened
    try:
        assert opened, "The operation must exercise real SQLite connections"
        for connection in opened:
            assert connection.close_calls == 1
            with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
                connection.execute("SELECT 1")
    finally:
        for connection in opened:
            if not connection.close_calls:
                connection.close()
        opened.clear()
        gc.collect()


def test_projection_operations_close_connections(tmp_path, connections):
    repository, canonical = _canonical_set(tmp_path)
    projection = SQLiteProjection(
        repository.roadmap_dir / "db/projection.db", repository
    )
    projection.rebuild()
    assert not projection.needs_rebuild()
    assert projection.inspect_state() == "current"
    assert projection.ensure_current() == "current"
    assert len(projection.query()) == 3

    issue = next(path for path in canonical if path.name == "issue-1.md")
    issue.write_text(issue.read_text().replace("A useful issue", "Manual edit"))
    assert projection.inspect_state() == "outdated"
    assert projection.ensure_current() == "refreshed"
    assert next(row for row in projection.query("issue"))["name"] == "Manual edit"
    projection.path.write_bytes(b"not a SQLite database")
    assert projection.inspect_state() == "corrupt"
    assert projection.ensure_current() == "rebuilt"
    assert len(projection.query()) == 3


@pytest.mark.parametrize("stage", ["schema", "insert", "commit", "refresh", "query"])
def test_projection_failures_close_connections_and_allow_retry(
    tmp_path, monkeypatch, connections, stage
):
    repository, canonical = _canonical_set(tmp_path)
    projection = SQLiteProjection(
        repository.roadmap_dir / "db/projection.db", repository
    )
    projection.rebuild()
    original = projection.path.read_bytes()

    def fail(*_args):
        raise sqlite3.OperationalError(f"injected {stage} failure")

    with monkeypatch.context() as patch:
        if stage == "schema":
            patch.setattr(projection, "_create_schema", fail)
        elif stage in {"insert", "refresh"}:
            patch.setattr(projection, "_insert", fail)
        elif stage == "commit":
            patch.setattr(type(connections[0]), "commit", fail)
        else:
            execute = type(connections[0]).execute

            def fail_query(connection, sql, *args):
                if sql.startswith("SELECT * FROM documents"):
                    return fail()
                return execute(connection, sql, *args)

            patch.setattr(type(connections[0]), "execute", fail_query)

        with pytest.raises(ProjectionError, match=f"injected {stage} failure"):
            if stage == "refresh":
                issue = next(path for path in canonical if path.name == "issue-1.md")
                issue.write_text(
                    issue.read_text().replace("A useful issue", "Manual edit")
                )
                projection.ensure_current()
            elif stage == "query":
                projection.query()
            else:
                projection.rebuild()

    assert projection.path.read_bytes() == original
    assert all(connection.close_calls == 1 for connection in connections)
    assert len(projection.query()) == 3
    assert projection.inspect_state() == "current"
