"""Workspace-atomic canonical document unit of work."""

from __future__ import annotations

import errno
import fcntl
import json
import logging
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
        try:
            metadata = (
                json.dumps({"pid": os.getpid(), "acquired_at": time.time()}) + "\n"
            )
            self._file.seek(0)
            self._file.truncate()
            self._file.write(metadata)
            self._file.flush()
            os.fsync(self._file.fileno())
        except BaseException as error:
            self.__exit__(type(error), error, error.__traceback__)
            raise
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


@dataclass(slots=True)
class _Delete:
    path: Path
    expected: str


@dataclass(slots=True)
class _RawWrite:
    path: Path
    content: bytes
    expected: str | None
    final: bool = False


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
        _sync_directory(path.parent)
    finally:
        if temp.exists():
            temp.unlink()


def _atomic_delete(path: Path) -> None:
    path.unlink(missing_ok=True)
    if not path.parent.exists():
        return
    _sync_directory(path.parent)


class CanonicalUnitOfWork:
    """Optimistic, recoverable write set over canonical Markdown documents."""

    def __init__(
        self,
        repository: DocumentRepository,
        projection: Any | None = None,
        *,
        timeout: float = 30.0,
        read_only: bool = False,
        failure_injector: Callable[[str, Path | None], None] | None = None,
    ):
        self.repository = repository
        self._read_only = read_only
        state_dir = repository.roadmap_dir / "db"
        self._lock = WorkspaceLock(state_dir / "canonical-write.lock", timeout)
        self._transactions = state_dir / "transactions"
        self._projection = projection
        self._inject = failure_injector or (lambda _stage, _path: None)
        self._loaded: dict[tuple[DocumentKind, EntityId], DocumentEnvelope] = {}
        self._identities: dict[Path, str | None] = {}
        self._writes: dict[tuple[DocumentKind, EntityId], _Write] = {}
        self._deletes: dict[tuple[DocumentKind, EntityId], _Delete] = {}
        self._raw_writes: dict[Path, _RawWrite] = {}
        self._raw_deletes: dict[Path, _Delete] = {}
        self.projection_stale = False
        self.cleanup_pending = False
        self._entered = False

    def __enter__(self) -> CanonicalUnitOfWork:
        self._lock.__enter__()
        self._entered = True
        try:
            if self._read_only:
                self._require_no_pending_transactions()
            else:
                self.recover()
        except BaseException as error:
            self._entered = False
            self._lock.__exit__(type(error), error, error.__traceback__)
            raise
        return self

    def _require_no_pending_transactions(self) -> None:
        try:
            pending = tuple(self._transactions.iterdir())
        except FileNotFoundError:
            return
        if pending:
            raise RecoveryError(
                "Cannot preview while canonical recovery is pending; run "
                "'roadmap health fix --fix-type recovery --dry-run' first"
            )

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

    def list_issues(self) -> tuple[Issue, ...]:
        self._require_lock()
        issues: list[Issue] = []
        for envelope in self.repository.scan("issue"):
            identity = envelope.aggregate.id
            self._loaded[("issue", identity)] = envelope
            digest = content_identity(envelope.path.read_bytes())
            self._identities[envelope.path] = digest
            if isinstance(envelope.aggregate, Issue):
                issues.append(envelope.aggregate)
        return tuple(issues)

    def _list(self, kind: DocumentKind, aggregate_type):
        self._require_lock()
        aggregates = []
        for envelope in self.repository.scan(kind):
            identity = envelope.aggregate.id
            self._loaded[(kind, identity)] = envelope
            self._identities[envelope.path] = content_identity(
                envelope.path.read_bytes()
            )
            if isinstance(envelope.aggregate, aggregate_type):
                aggregates.append(envelope.aggregate)
        return tuple(aggregates)

    def list_milestones(self) -> tuple[Milestone, ...]:
        return self._list("milestone", Milestone)

    def list_projects(self) -> tuple[Project, ...]:
        return self._list("project", Project)

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

    def delete_issue(self, issue_id: EntityId) -> bool:
        return self._delete("issue", issue_id)

    def _delete(self, kind: DocumentKind, identity: EntityId) -> bool:
        self._require_lock()
        key = (kind, identity)
        envelope = self._loaded.get(key)
        if envelope is None:
            found = self.repository.load(kind, identity)
            if found is None:
                return False
            envelope = found
            self._loaded[key] = envelope
            self._identities[envelope.path] = content_identity(
                envelope.path.read_bytes()
            )
        expected = self._identities[envelope.path]
        assert expected is not None
        self._writes.pop(key, None)
        self._deletes[key] = _Delete(envelope.path, expected)
        return True

    def delete_milestone(self, milestone_id: EntityId) -> bool:
        return self._delete("milestone", milestone_id)

    def delete_project(self, project_id: EntityId) -> bool:
        return self._delete("project", project_id)

    def save_milestone(self, milestone: Milestone) -> None:
        self._save("milestone", milestone)

    def save_project(self, project: Project) -> None:
        self._save("project", project)

    def stage_file(self, relative: str, content: bytes, *, final: bool = False) -> None:
        """Stage an enumerated workspace file for migration or recovery."""
        self._require_lock()
        path = self._target(relative)
        expected = content_identity(path.read_bytes()) if path.exists() else None
        self._raw_deletes.pop(path, None)
        self._raw_writes[path] = _RawWrite(path, content, expected, final)

    def stage_delete(self, relative: str) -> None:
        """Stage deletion of one enumerated workspace file."""
        self._require_lock()
        path = self._target(relative)
        self._raw_writes.pop(path, None)
        if path.exists():
            self._raw_deletes[path] = _Delete(path, content_identity(path.read_bytes()))

    @staticmethod
    def _ensure_unchanged(path: Path, expected: str | None, label: str) -> None:
        actual = content_identity(path.read_bytes()) if path.exists() else None
        if actual != expected:
            raise CanonicalConflict(f"canonical {label} changed: {path}")

    def _validate(self) -> None:
        for write in self._writes.values():
            self._ensure_unchanged(write.envelope.path, write.expected, "document")
        for deletion in self._deletes.values():
            self._ensure_unchanged(deletion.path, deletion.expected, "document")
        for write in self._raw_writes.values():
            self._ensure_unchanged(write.path, write.expected, "file")
        for deletion in self._raw_deletes.values():
            self._ensure_unchanged(deletion.path, deletion.expected, "file")

    def _write_entry(
        self, directory: Path, index: int, path: Path, content: bytes
    ) -> dict[str, Any]:
        before_name = f"{index}.before"
        after_name = f"{index}.after"
        before = path.read_bytes() if path.exists() else None
        if before is not None:
            _atomic_write(directory / before_name, before)
        _atomic_write(directory / after_name, content)
        return {
            "target": str(path.relative_to(self.repository.roadmap_dir)),
            "before": before_name if before is not None else None,
            "after": after_name,
            "before_digest": content_identity(before) if before is not None else None,
            "after_digest": content_identity(content),
        }

    def _delete_entry(self, directory: Path, index: int, path: Path) -> dict[str, Any]:
        before_name = f"{index}.before"
        before = path.read_bytes()
        _atomic_write(directory / before_name, before)
        return {
            "target": str(path.relative_to(self.repository.roadmap_dir)),
            "before": before_name,
            "after": None,
            "before_digest": content_identity(before),
            "after_digest": None,
        }

    def _journal(self, directory: Path) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for index, write in enumerate(self._writes.values()):
            entries.append(
                self._write_entry(
                    directory,
                    index,
                    write.envelope.path,
                    serialize_document(write.envelope),
                )
            )
        offset = len(entries)
        for index, deletion in enumerate(self._deletes.values(), start=offset):
            entries.append(self._delete_entry(directory, index, deletion.path))
        offset = len(entries)
        ordinary_writes = tuple(
            write for write in self._raw_writes.values() if not write.final
        )
        final_writes = tuple(
            write for write in self._raw_writes.values() if write.final
        )
        for index, write in enumerate(ordinary_writes, start=offset):
            entries.append(
                self._write_entry(directory, index, write.path, write.content)
            )
        offset = len(entries)
        for index, deletion in enumerate(self._raw_deletes.values(), start=offset):
            entries.append(self._delete_entry(directory, index, deletion.path))
        offset = len(entries)
        for index, write in enumerate(final_writes, start=offset):
            entries.append(
                self._write_entry(directory, index, write.path, write.content)
            )
        journal = directory / "journal.json"
        _atomic_write(
            journal, json.dumps({"state": "prepared", "entries": entries}).encode()
        )
        return entries

    @staticmethod
    def _snapshot(directory: Path, entry: dict[str, Any], side: str) -> bytes | None:
        name = entry[side]
        if name is None:
            return None
        if not isinstance(name, str) or Path(name).name != name:
            raise RecoveryError("transaction snapshot must be a local filename")
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise RecoveryError(f"transaction snapshot is missing or unsafe: {name}")
        content = path.read_bytes()
        digest = entry.get(f"{side}_digest")
        if digest is not None and content_identity(content) != digest:
            raise RecoveryError(f"transaction snapshot is corrupt: {name}")
        return content

    def _validate_recovery(
        self, directory: Path, entries: list[dict[str, Any]]
    ) -> None:
        if not isinstance(entries, list) or not entries:
            raise RecoveryError("transaction entries must be a nonempty list")
        targets: set[Path] = set()
        for entry in entries:
            target = self._target(entry["target"])
            if target in targets:
                raise RecoveryError(f"duplicate transaction target: {target}")
            targets.add(target)
            before = self._snapshot(directory, entry, "before")
            after = self._snapshot(directory, entry, "after")
            current = target.read_bytes() if target.exists() else None
            if current not in (before, after):
                raise RecoveryError(
                    f"transaction target changed after interruption: {target}"
                )

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
            if entry["after"] is None:
                _atomic_delete(target)
            else:
                _atomic_write(target, (directory / entry["after"]).read_bytes())
            self._inject("after_replace", target)

    def _restore(self, directory: Path, entries: list[dict[str, Any]]) -> None:
        for entry in entries:
            target = self._target(entry["target"])
            before = entry["before"]
            if before is None:
                if target.exists():
                    _atomic_delete(target)
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
            if directory.name.startswith((".preparing-", ".completed-")):
                self._discard_transaction(directory)
                continue
            journal = directory / "journal.json"
            try:
                payload = json.loads(journal.read_text())
                if payload["state"] not in {"prepared", "rollback"}:
                    raise RecoveryError("unknown transaction state")
                entries = payload["entries"]
                self._validate_recovery(directory, entries)
                if payload["state"] == "rollback":
                    self._restore(directory, entries)
                else:
                    self._apply(directory, entries)
            except Exception as error:
                raise RecoveryError(
                    f"cannot recover transaction {directory.name}: {error}"
                ) from error
            self._discard_transaction(directory)
            recovered += 1
        return recovered

    def _discard_transaction(self, directory: Path) -> None:
        if not directory.name.startswith(".completed-"):
            identity = directory.name.removeprefix(".preparing-")
            completed = directory.with_name(f".completed-{identity}")
            directory.rename(completed)
            directory = completed
            _sync_directory(self._transactions)
        self._inject("before_cleanup", directory)
        shutil.rmtree(directory)
        _sync_directory(self._transactions)

    def commit(self) -> None:
        self._require_lock()
        if self._read_only:
            raise RuntimeError("Cannot commit a read-only preview")
        if (
            not self._writes
            and not self._deletes
            and not self._raw_writes
            and not self._raw_deletes
        ):
            return
        self._inject("before_validate", None)
        self._validate()
        self._inject("after_validate", None)
        self._transactions.mkdir(parents=True, exist_ok=True)
        _sync_directory(self._transactions.parent)
        identity = uuid.uuid4().hex
        directory = self._transactions / f".preparing-{identity}"
        directory.mkdir()
        entries: list[dict[str, Any]] = []
        try:
            self._inject("before_journal", directory)
            entries = self._journal(directory)
            prepared = self._transactions / identity
            directory.rename(prepared)
            directory = prepared
            _sync_directory(self._transactions)
            self._inject("after_journal", directory)
            self._apply(directory, entries)
        except Exception:
            if entries:
                _atomic_write(
                    directory / "journal.json",
                    json.dumps({"state": "rollback", "entries": entries}).encode(),
                )
                self._restore(directory, entries)
            self._discard_transaction(directory)
            raise
        # All canonical replacements are durable here. Maintenance failures
        # must not report a failed mutation and encourage a duplicate retry.
        try:
            self._discard_transaction(directory)
        except OSError:
            self.cleanup_pending = True
            logging.getLogger(__name__).warning(
                "Canonical commit succeeded; transaction cleanup will retry on reopen",
                exc_info=True,
            )
        changed_ids = tuple(key[1] for key in (*self._writes, *self._deletes))
        self._writes.clear()
        self._deletes.clear()
        self._raw_writes.clear()
        self._raw_deletes.clear()
        self._refresh_projection(changed_ids)

    def _refresh_projection(self, changed_ids: tuple[EntityId, ...]) -> None:
        if self._projection is not None:
            try:
                self._projection.refresh(changed_ids)
            except Exception:
                self.projection_stale = True
                logging.getLogger(__name__).warning(
                    "Canonical commit succeeded; projection refresh failed; rebuild the projection",
                    exc_info=True,
                )
                try:
                    self._projection.mark_stale()
                except Exception:
                    logging.getLogger(__name__).warning(
                        "Canonical commit succeeded; projection stale marker could not be written",
                        exc_info=True,
                    )

    def rollback(self) -> None:
        self._writes.clear()
        self._deletes.clear()
        self._raw_writes.clear()
        self._raw_deletes.clear()


class CanonicalIssueUnitOfWorkFactory:
    """Create one workspace-locked unit of work per Application mutation."""

    def __init__(self, repository: DocumentRepository, projection: Any | None = None):
        self._repository = repository
        self._projection = projection

    def create(self, *, read_only: bool = False) -> CanonicalUnitOfWork:
        return CanonicalUnitOfWork(
            self._repository, self._projection, read_only=read_only
        )
