"""Workspace-atomic canonical document unit of work."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import shutil
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import EntityId

from .documents import (
    Aggregate,
    DocumentEnvelope,
    DocumentKind,
    DocumentRepository,
    content_identity,
    serialize_document,
)


class CanonicalConflict(RuntimeError):
    """Canonical content changed after it entered this write set."""


class RecoveryError(RuntimeError):
    """An interrupted canonical transaction cannot be recovered safely."""


class WorkspaceBusy(RuntimeError):
    """Another writer owns the workspace mutation lock."""


class WorkspaceLock:
    """One diagnostic advisory lock for every mutation in a workspace."""

    def __init__(self, path: Path, timeout: float = 30.0):
        self.path = path
        self.timeout = timeout
        self._file = None

    def __enter__(self) -> WorkspaceLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+", encoding="utf-8")
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN):
                    self._file.close()
                    raise
                if time.monotonic() >= deadline:
                    self._file.close()
                    raise WorkspaceBusy(
                        f"workspace lock timed out: {self.path}"
                    ) from error
                time.sleep(0.05)
        metadata = json.dumps({"pid": os.getpid(), "acquired_at": time.time()})
        self._file.seek(0)
        self._file.truncate()
        self._file.write(metadata)
        self._file.flush()
        os.fsync(self._file.fileno())
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        if self._file is not None:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            self._file.close()
            self._file = None


@dataclass(slots=True)
class _Write:
    envelope: DocumentEnvelope
    expected: str | None


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temp.exists():
            temp.unlink()


class CanonicalUnitOfWork:
    """Optimistic, recoverable write set over canonical Markdown documents."""

    def __init__(
        self,
        repository: DocumentRepository,
        projection: Any | None = None,
        *,
        timeout: float = 30.0,
        failure_injector: Callable[[str, Path | None], None] | None = None,
    ):
        self.repository = repository
        state_dir = repository.roadmap_dir / "db"
        self._lock = WorkspaceLock(state_dir / "canonical-write.lock", timeout)
        self._transactions = state_dir / "transactions"
        self._projection = projection
        self._inject = failure_injector or (lambda _stage, _path: None)
        self._loaded: dict[tuple[DocumentKind, EntityId], DocumentEnvelope] = {}
        self._identities: dict[Path, str | None] = {}
        self._writes: dict[tuple[DocumentKind, EntityId], _Write] = {}
        self.projection_stale = False
        self._entered = False

    def __enter__(self) -> CanonicalUnitOfWork:
        self._lock.__enter__()
        self._entered = True
        self.recover()
        return self

    def __exit__(self, exc_type, _exc, _tb) -> None:
        if exc_type is not None:
            self.rollback()
        self._entered = False
        self._lock.__exit__(exc_type, _exc, _tb)

    def _require_lock(self) -> None:
        if not self._entered:
            raise RuntimeError("canonical unit of work must be entered")

    def _load(self, kind: DocumentKind, identity: EntityId):
        self._require_lock()
        envelope = self.repository.load(kind, identity)
        if envelope is not None:
            self._loaded[(kind, identity)] = envelope
            self._identities[envelope.path] = content_identity(
                envelope.path.read_bytes()
            )
            return envelope.aggregate
        return None

    def load_issue(self, issue_id: EntityId) -> Issue | None:
        aggregate = self._load("issue", issue_id)
        return aggregate if isinstance(aggregate, Issue) else None

    def load_milestone(self, milestone_id: EntityId) -> Milestone | None:
        aggregate = self._load("milestone", milestone_id)
        return aggregate if isinstance(aggregate, Milestone) else None

    def load_project(self, project_id: EntityId) -> Project | None:
        aggregate = self._load("project", project_id)
        return aggregate if isinstance(aggregate, Project) else None

    def _save(self, kind: DocumentKind, aggregate: Aggregate) -> None:
        self._require_lock()
        key = (kind, aggregate.id)
        current = self._loaded.get(key)
        if current is None:
            found = self.repository.load(kind, aggregate.id)
            if found is None:
                path = self.repository.default_path(kind, aggregate)
                current = DocumentEnvelope(kind, aggregate, path, {})
                self._identities.setdefault(path, None)
            else:
                current = found
                self._identities[current.path] = content_identity(
                    current.path.read_bytes()
                )
        envelope = replace(current, aggregate=aggregate, schema_version=1)
        self._writes[key] = _Write(envelope, self._identities[envelope.path])

    def save_issue(self, issue: Issue) -> None:
        self._save("issue", issue)

    def save_milestone(self, milestone: Milestone) -> None:
        self._save("milestone", milestone)

    def save_project(self, project: Project) -> None:
        self._save("project", project)

    def _validate(self) -> None:
        for write in self._writes.values():
            path = write.envelope.path
            actual = content_identity(path.read_bytes()) if path.exists() else None
            if actual != write.expected:
                raise CanonicalConflict(f"canonical document changed: {path}")

    def _journal(self, directory: Path) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for index, write in enumerate(self._writes.values()):
            path = write.envelope.path
            before_name = f"{index}.before"
            after_name = f"{index}.after"
            if path.exists():
                (directory / before_name).write_bytes(path.read_bytes())
            (directory / after_name).write_bytes(serialize_document(write.envelope))
            entries.append(
                {
                    "target": str(path.relative_to(self.repository.roadmap_dir)),
                    "before": before_name if path.exists() else None,
                    "after": after_name,
                }
            )
        journal = directory / "journal.json"
        journal.write_text(json.dumps({"state": "prepared", "entries": entries}))
        with journal.open("rb") as stream:
            os.fsync(stream.fileno())
        return entries

    def _target(self, relative: str) -> Path:
        target = (self.repository.roadmap_dir / relative).resolve()
        root = self.repository.roadmap_dir.resolve()
        if not target.is_relative_to(root):
            raise RecoveryError(f"transaction target escapes workspace: {relative}")
        return target

    def _apply(self, directory: Path, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            target = self._target(entry["target"])
            self._inject("before_replace", target)
            _atomic_write(target, (directory / entry["after"]).read_bytes())
            self._inject("after_replace", target)

    def _restore(self, directory: Path, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            target = self._target(entry["target"])
            before = entry["before"]
            if before is None:
                if target.exists():
                    target.unlink()
            else:
                _atomic_write(target, (directory / before).read_bytes())

    def recover(self) -> int:
        """Roll interrupted prepared transactions forward under the workspace lock."""
        self._require_lock()
        recovered = 0
        if not self._transactions.exists():
            return recovered
        for directory in sorted(
            path for path in self._transactions.iterdir() if path.is_dir()
        ):
            journal = directory / "journal.json"
            try:
                payload = json.loads(journal.read_text())
                entries = payload["entries"]
                self._apply(directory, entries)
            except Exception as error:
                raise RecoveryError(
                    f"cannot recover transaction {directory.name}"
                ) from error
            shutil.rmtree(directory)
            recovered += 1
        return recovered

    def commit(self) -> None:
        self._require_lock()
        if not self._writes:
            return
        self._inject("before_validate", None)
        self._validate()
        self._inject("after_validate", None)
        self._transactions.mkdir(parents=True, exist_ok=True)
        directory = self._transactions / uuid.uuid4().hex
        directory.mkdir()
        entries: list[dict[str, Any]] = []
        try:
            entries = self._journal(directory)
            self._inject("after_journal", directory)
            self._apply(directory, entries)
        except Exception:
            if entries:
                self._restore(directory, entries)
            shutil.rmtree(directory, ignore_errors=True)
            raise
        shutil.rmtree(directory)
        changed_ids = tuple(key[1] for key in self._writes)
        self._writes.clear()
        if self._projection is not None:
            try:
                self._projection.refresh(changed_ids)
            except Exception:
                self.projection_stale = True
                self._projection.mark_stale()

    def rollback(self) -> None:
        self._writes.clear()
