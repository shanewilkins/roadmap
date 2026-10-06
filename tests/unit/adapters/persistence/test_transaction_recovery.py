"""Failure boundaries where recovery must preserve user-authored state."""

from __future__ import annotations

import errno
import fcntl
import json
import os
from pathlib import Path

import pytest

from roadmap.adapters.outbound.persistence.canonical import (
    CanonicalUnitOfWork,
    RecoveryError,
    WorkspaceLock,
)
from roadmap.adapters.outbound.persistence.documents import DocumentRepository


def _pending(root: Path) -> Path:
    def interrupt(stage: str, _path: Path | None) -> None:
        if stage == "after_journal":
            raise SystemExit("interrupted")

    with pytest.raises(SystemExit):
        with CanonicalUnitOfWork(
            DocumentRepository(root), failure_injector=interrupt
        ) as unit:
            unit.stage_file("first.txt", b"new first")
            unit.stage_file("second.txt", b"new second")
            unit.commit()
    return next((root / "db/transactions").iterdir())


def test_unknown_journal_state_preserves_files_and_recovery_evidence(tmp_path):
    root = tmp_path / ".roadmap"
    directory = _pending(root)
    journal = directory / "journal.json"
    payload = json.loads(journal.read_text())
    payload["state"] = "unrecognized"
    journal.write_text(json.dumps(payload))
    before = {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and p.name != "canonical-write.lock"
    }
    with pytest.raises(RecoveryError, match="state"):
        with CanonicalUnitOfWork(DocumentRepository(root)):
            pass
    assert {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and p.name != "canonical-write.lock"
    } == before
    with WorkspaceLock(root / "db/canonical-write.lock", timeout=0):
        pass


def test_failure_before_journal_leaves_no_pending_transaction_and_allows_retry(
    tmp_path,
):
    root = tmp_path / ".roadmap"
    root.mkdir()
    target = root / "first.txt"
    target.write_bytes(b"original")

    def fail(stage, _path):
        if stage == "before_journal":
            raise OSError(errno.ENOSPC, "disk full")

    with CanonicalUnitOfWork(DocumentRepository(root), failure_injector=fail) as unit:
        unit.stage_file("first.txt", b"replacement")
        with pytest.raises(OSError) as failure:
            unit.commit()
        assert failure.value.errno == errno.ENOSPC
    assert target.read_bytes() == b"original"
    assert not list((root / "db/transactions").iterdir())
    with CanonicalUnitOfWork(DocumentRepository(root)) as unit:
        unit.stage_file("first.txt", b"replacement")
        unit.commit()
    assert target.read_bytes() == b"replacement"


def test_unexpected_lock_error_closes_descriptor_and_preserves_errno(
    tmp_path, monkeypatch
):
    lock = WorkspaceLock(tmp_path / "write.lock", timeout=0)
    with monkeypatch.context() as patch:

        def fail(_descriptor, _operation):
            raise OSError(errno.EIO, "lock device failure")

        patch.setattr(fcntl, "flock", fail)
        with pytest.raises(OSError) as failure:
            lock.__enter__()
        assert failure.value.errno == errno.EIO
        assert lock._file is not None
        assert lock._file.closed
    with WorkspaceLock(lock.path, timeout=0):
        pass


def test_read_only_commit_refuses_writes_and_missing_deletion_is_repeatable(tmp_path):
    repository = DocumentRepository(tmp_path / ".roadmap")
    with CanonicalUnitOfWork(repository, read_only=True) as unit:
        with pytest.raises(RuntimeError, match="read.only"):
            unit.commit()
    with CanonicalUnitOfWork(repository) as unit:
        from roadmap.domain.types import EntityId

        assert not unit.delete_issue(EntityId("absent"))
        assert not unit.delete_issue(EntityId("absent"))
        unit.commit()
    assert not repository.scan()


@pytest.mark.parametrize(
    "damage",
    [
        "missing-snapshot",
        "corrupt-snapshot",
        "invalid-journal",
        "external-edit",
        "escaping-snapshot",
        "escaping-target",
        "snapshot-symlink",
        "duplicate-target",
        "empty-journal",
    ],
)
def test_recovery_validates_entire_transaction_before_changing_files(tmp_path, damage):
    root = tmp_path / ".roadmap"
    root.mkdir()
    (root / "first.txt").write_bytes(b"old first")
    (root / "second.txt").write_bytes(b"old second")
    directory = _pending(root)
    if damage == "missing-snapshot":
        (directory / "1.after").unlink()
    elif damage == "corrupt-snapshot":
        (directory / "1.after").write_bytes(b"damaged snapshot")
    elif damage == "invalid-journal":
        (directory / "journal.json").write_text('{"entries": [')
    elif damage == "external-edit":
        (root / "second.txt").write_bytes(b"manual edit after interruption")
    elif damage == "escaping-snapshot":
        journal = directory / "journal.json"
        payload = json.loads(journal.read_text())
        payload["entries"][1]["after"] = "../../../../outside.txt"
        (tmp_path / "outside.txt").write_bytes(b"outside data")
        journal.write_text(json.dumps(payload))
    elif damage in {"escaping-target", "duplicate-target"}:
        journal = directory / "journal.json"
        payload = json.loads(journal.read_text())
        payload["entries"][1]["target"] = (
            "../outside.txt" if damage == "escaping-target" else "first.txt"
        )
        journal.write_text(json.dumps(payload))
    elif damage == "snapshot-symlink":
        outside = tmp_path / "outside.txt"
        outside.write_bytes((directory / "1.after").read_bytes())
        (directory / "1.after").unlink()
        (directory / "1.after").symlink_to(outside)
    else:
        (directory / "journal.json").write_text('{"state": "prepared", "entries": []}')
    before = {p.name: p.read_bytes() for p in root.glob("*.txt")}

    with pytest.raises(RecoveryError):
        with CanonicalUnitOfWork(DocumentRepository(root)):
            pass

    assert {p.name: p.read_bytes() for p in root.glob("*.txt")} == before
    assert directory.exists(), "failed recovery must retain its evidence"


def test_failed_recovery_releases_lock_even_when_unit_is_retained(tmp_path):
    root = tmp_path / ".roadmap"
    directory = _pending(root)
    (directory / "journal.json").write_text("invalid JSON")
    unit = CanonicalUnitOfWork(DocumentRepository(root))

    with pytest.raises(RecoveryError):
        unit.__enter__()

    with WorkspaceLock(root / "db/canonical-write.lock", timeout=0.05):
        pass
    with pytest.raises(RuntimeError, match="must be entered"):
        unit.recover()


def test_legacy_journal_without_snapshot_digests_still_recovers(tmp_path):
    root = tmp_path / ".roadmap"
    directory = _pending(root)
    journal = directory / "journal.json"
    payload = json.loads(journal.read_text())
    for entry in payload["entries"]:
        entry.pop("before_digest")
        entry.pop("after_digest")
    journal.write_text(json.dumps(payload))
    with CanonicalUnitOfWork(DocumentRepository(root)):
        pass
    assert (root / "first.txt").read_bytes() == b"new first"
    assert (root / "second.txt").read_bytes() == b"new second"
    assert not list((root / "db/transactions").iterdir())


@pytest.mark.parametrize("error_number", [errno.EACCES, errno.ENOSPC])
def test_replacement_failure_restores_all_files_and_allows_retry(
    tmp_path, monkeypatch, error_number
):
    root = tmp_path / ".roadmap"
    root.mkdir()
    first, second = root / "first.txt", root / "second.txt"
    first.write_bytes(b"old first")
    second.write_bytes(b"old second")
    replace = os.replace
    failed = False

    def fail_once(source, target):
        nonlocal failed
        if Path(target) == second and not failed:
            failed = True
            raise OSError(error_number, os.strerror(error_number))
        return replace(source, target)

    monkeypatch.setattr(os, "replace", fail_once)
    with CanonicalUnitOfWork(DocumentRepository(root)) as unit:
        unit.stage_file("first.txt", b"new first")
        unit.stage_file("second.txt", b"new second")
        with pytest.raises(OSError) as error:
            unit.commit()
        assert error.value.errno == error_number
    assert first.read_bytes() == b"old first"
    assert second.read_bytes() == b"old second"
    assert not list((root / "db/transactions").iterdir())

    with CanonicalUnitOfWork(DocumentRepository(root)) as retry:
        retry.stage_file("first.txt", b"new first")
        retry.stage_file("second.txt", b"new second")
        retry.commit()
    assert first.read_bytes() == b"new first"
    assert second.read_bytes() == b"new second"


def test_failed_rollback_is_retried_as_rollback_not_as_new_commit(
    tmp_path, monkeypatch
):
    root = tmp_path / ".roadmap"
    root.mkdir()
    first, second = root / "first.txt", root / "second.txt"
    first.write_bytes(b"old first")
    second.write_bytes(b"old second")
    replace = os.replace
    replacements = 0

    def fail_commit_and_restore(source, target):
        nonlocal replacements
        if Path(target) in {first, second}:
            replacements += 1
            if replacements in {2, 3}:
                raise PermissionError("temporarily unavailable")
        return replace(source, target)

    monkeypatch.setattr(os, "replace", fail_commit_and_restore)
    with CanonicalUnitOfWork(DocumentRepository(root)) as unit:
        unit.stage_file("first.txt", b"new first")
        unit.stage_file("second.txt", b"new second")
        with pytest.raises(PermissionError):
            unit.commit()
    directory = next((root / "db/transactions").iterdir())
    assert json.loads((directory / "journal.json").read_text())["state"] == "rollback"
    with CanonicalUnitOfWork(DocumentRepository(root)):
        pass
    assert first.read_bytes() == b"old first"
    assert second.read_bytes() == b"old second"
    assert not list((root / "db/transactions").iterdir())


def test_lock_metadata_failure_releases_kernel_lock(tmp_path, monkeypatch):
    fsync = os.fsync
    failed = False

    def fail_once(descriptor):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError(errno.ENOSPC, "disk full")
        return fsync(descriptor)

    monkeypatch.setattr(os, "fsync", fail_once)
    lock = WorkspaceLock(tmp_path / "write.lock")
    with pytest.raises(OSError, match="disk full"):
        lock.__enter__()
    with WorkspaceLock(tmp_path / "write.lock", timeout=0.05):
        pass
