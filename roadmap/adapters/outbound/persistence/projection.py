"""Disposable one-way SQLite projection of canonical documents."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any

from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.requirement_relations import RequirementRelationKind
from roadmap.domain.requirements import Requirement
from roadmap.domain.types import EntityId

from .documents import DocumentEnvelope, DocumentRepository, content_identity

PROJECTION_SCHEMA_VERSION = 2


class ProjectionError(RuntimeError):
    """Projection maintenance failed; canonical state remains committed."""


class SQLiteProjection:
    """Rebuildable query index that has no operation capable of writing documents."""

    def __init__(self, path: Path, repository: DocumentRepository):
        self.path = path
        self.repository = repository
        self.stale_path = path.with_suffix(path.suffix + ".stale")

    @contextmanager
    def _connection(self, path: Path | None = None):
        target = path or self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with closing(sqlite3.connect(target)) as connection:
                connection.row_factory = sqlite3.Row
                yield connection
                connection.commit()
        except sqlite3.Error as error:
            raise ProjectionError(f"SQLite projection failed: {error}") from error

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE projection_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE documents (
                kind TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                digest TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                retention TEXT NOT NULL,
                attributes TEXT NOT NULL,
                PRIMARY KEY (kind, entity_id)
            );
            CREATE INDEX documents_status ON documents(kind, status);
            CREATE TABLE requirement_relations (
                source_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                target_kind TEXT NOT NULL,
                target TEXT NOT NULL,
                PRIMARY KEY (source_id, relation, target)
            );
            CREATE INDEX requirement_relations_reverse
            ON requirement_relations(relation, target);
            """
        )
        connection.execute(
            "INSERT INTO projection_meta(key, value) VALUES ('schema_version', ?)",
            (str(PROJECTION_SCHEMA_VERSION),),
        )

    def _row(self, envelope: DocumentEnvelope) -> tuple[str, ...]:
        aggregate = envelope.aggregate
        name = str(
            aggregate.definition.title
            if isinstance(aggregate, Requirement)
            else aggregate.title
            if isinstance(aggregate, Issue)
            else aggregate.name
        )
        attributes: dict[str, Any] = {}
        if isinstance(aggregate, Issue):
            attributes = {
                "priority": aggregate.priority.value,
                "issue_type": aggregate.issue_type.value,
                "milestone_id": aggregate.relations.milestone_id,
                "labels": aggregate.labels,
                "assignee": aggregate.assignee,
            }
        elif isinstance(aggregate, Milestone):
            attributes = {"project_id": aggregate.relation.project_id}
        elif isinstance(aggregate, Requirement):
            attributes = {
                "key": str(aggregate.key),
                "requirement_type": aggregate.definition.kind.value,
                "priority": aggregate.priority.value,
                "owner": aggregate.owner,
                "revision": aggregate.current_revision,
            }
        elif isinstance(aggregate, Project):
            attributes = {
                "priority": aggregate.priority.value,
                "milestone_ids": aggregate.relations.milestone_ids,
                "owner": aggregate.owner,
            }
        return (
            envelope.kind,
            envelope.identity,
            str(envelope.path.relative_to(self.repository.roadmap_dir)),
            content_identity(envelope.path.read_bytes()),
            name,
            (
                aggregate.effective_status.value
                if isinstance(aggregate, Requirement)
                else aggregate.status.value
            ),
            aggregate.retention.value,
            json.dumps(attributes, sort_keys=True),
        )

    def _insert(
        self, connection: sqlite3.Connection, envelope: DocumentEnvelope
    ) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO documents
            (kind, entity_id, path, digest, name, status, retention, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._row(envelope),
        )
        aggregate = envelope.aggregate
        if isinstance(aggregate, Requirement):
            connection.execute(
                "DELETE FROM requirement_relations WHERE source_id = ?",
                (str(aggregate.id),),
            )
            connection.executemany(
                """
                INSERT INTO requirement_relations
                (source_id, relation, target_kind, target)
                VALUES (?, ?, ?, ?)
                """,
                self._relation_rows(aggregate),
            )

    @staticmethod
    def _relation_rows(
        requirement: Requirement,
    ) -> tuple[tuple[str, str, str, str], ...]:
        source = str(requirement.id)
        rows: list[tuple[str, str, str, str]] = []
        relation_targets = (
            (RequirementRelationKind.SUPPORTS, "requirement"),
            (RequirementRelationKind.DEPENDS_ON, "requirement"),
            (RequirementRelationKind.IMPLEMENTED_BY, "issue"),
            (RequirementRelationKind.PROJECT_TARGET, "project"),
            (RequirementRelationKind.MILESTONE_TARGET, "milestone"),
            (RequirementRelationKind.EVIDENCE, "evidence"),
            (RequirementRelationKind.REPORT, "report"),
        )
        for relation, target_kind in relation_targets:
            rows.extend(
                (source, relation.value, target_kind, target)
                for target in requirement.relation_targets(relation)
            )
        return tuple(rows)

    def _is_compatible(self) -> bool:
        if not self.path.exists() or self.stale_path.exists():
            return False
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT value FROM projection_meta WHERE key = 'schema_version'"
                ).fetchone()
                integrity = connection.execute("PRAGMA quick_check").fetchone()
                return bool(
                    row
                    and int(row[0]) == PROJECTION_SCHEMA_VERSION
                    and integrity
                    and integrity[0] == "ok"
                )
        except (ProjectionError, ValueError):
            return False

    def mark_stale(self) -> None:
        self.stale_path.parent.mkdir(parents=True, exist_ok=True)
        self.stale_path.write_text("canonical state is newer than this projection\n")

    def needs_rebuild(self) -> bool:
        """Report projection state without changing canonical or derived files."""
        return not self._is_compatible()

    def inspect_state(self) -> str:
        """Inspect compatibility and content identity without refreshing state."""
        if not self.path.exists():
            return "missing"
        if self.stale_path.exists():
            return "stale"
        if not self._is_compatible():
            return "corrupt"
        canonical = {
            (item.kind, item.identity): content_identity(item.path.read_bytes())
            for item in self.repository.scan()
        }
        try:
            with self._connection() as connection:
                projected = {
                    (row["kind"], row["entity_id"]): row["digest"]
                    for row in connection.execute(
                        "SELECT kind, entity_id, digest FROM documents"
                    )
                }
        except ProjectionError:
            return "corrupt"
        return "current" if canonical == projected else "outdated"

    def rebuild(self) -> None:
        """Replace any missing, corrupt, or incompatible projection from documents."""
        envelopes = self.repository.scan()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, raw_temp = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent
        )
        os.close(descriptor)
        temp = Path(raw_temp)
        try:
            temp.unlink()
            with self._connection(temp) as connection:
                self._create_schema(connection)
                for envelope in envelopes:
                    self._insert(connection, envelope)
            os.replace(temp, self.path)
            self.stale_path.unlink(missing_ok=True)
        except Exception:
            temp.unlink(missing_ok=True)
            self.mark_stale()
            raise

    def refresh(self, changed_ids: tuple[EntityId, ...]) -> None:
        """Refresh only identities affected by a successful canonical commit."""
        if not self._is_compatible():
            self.rebuild()
            return
        changed = {str(identity) for identity in changed_ids}
        envelopes = [
            envelope
            for envelope in self.repository.scan()
            if envelope.identity in changed
        ]
        try:
            with self._connection() as connection:
                connection.executemany(
                    "DELETE FROM documents WHERE entity_id = ?",
                    ((identity,) for identity in changed),
                )
                connection.executemany(
                    "DELETE FROM requirement_relations WHERE source_id = ?",
                    ((identity,) for identity in changed),
                )
                for envelope in envelopes:
                    self._insert(connection, envelope)
            self.stale_path.unlink(missing_ok=True)
        except Exception:
            self.mark_stale()
            raise

    def ensure_current(self) -> str:
        """Detect external edits/deletes and incrementally refresh or rebuild."""
        if not self._is_compatible():
            self.rebuild()
            return "rebuilt"
        canonical_files = {
            str(path.relative_to(self.repository.roadmap_dir)): content_identity(
                path.read_bytes()
            )
            for _kind, path in self.repository.paths()
        }
        with self._connection() as connection:
            projected_files = {
                row["path"]: row["digest"]
                for row in connection.execute("SELECT path, digest FROM documents")
            }
        if canonical_files == projected_files:
            return "current"

        envelopes = self.repository.scan()
        canonical = {
            (item.kind, item.identity): content_identity(item.path.read_bytes())
            for item in envelopes
        }
        with self._connection() as connection:
            projected = {
                (row["kind"], row["entity_id"]): row["digest"]
                for row in connection.execute(
                    "SELECT kind, entity_id, digest FROM documents"
                )
            }
        changed = {
            EntityId(identity)
            for kind, identity in canonical.keys() | projected.keys()
            if canonical.get((kind, identity)) != projected.get((kind, identity))
        }
        if not changed:
            return "current"
        self.refresh(tuple(sorted(changed)))
        return "refreshed"

    def query(self, kind: str | None = None) -> list[dict[str, Any]]:
        """Return derived candidate rows; callers still load canonical documents."""
        self.ensure_current()
        sql = "SELECT * FROM documents"
        parameters: tuple[str, ...] = ()
        if kind is not None:
            sql += " WHERE kind = ?"
            parameters = (kind,)
        sql += " ORDER BY kind, entity_id"
        with self._connection() as connection:
            return [dict(row) for row in connection.execute(sql, parameters)]

    def requirement_sources(self, relation: str, target: str) -> tuple[str, ...]:
        """Return deterministic reverse requirement IDs from the derived index."""
        kind = RequirementRelationKind(relation)
        self.ensure_current()
        with self._connection() as connection:
            return tuple(
                row["source_id"]
                for row in connection.execute(
                    """
                    SELECT source_id FROM requirement_relations
                    WHERE relation = ? AND target = ?
                    ORDER BY source_id
                    """,
                    (kind.value, target),
                )
            )
