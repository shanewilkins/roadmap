"""Child-process writer used to exercise kernel locks and abrupt termination."""

from __future__ import annotations

import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from roadmap.adapters.outbound.persistence.canonical import CanonicalUnitOfWork
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.migration import FilesystemWorkspaceMigration
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.domain.types import EntityId, Name, Timestamp, Title


def main() -> None:
    root, operation, checkpoint = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    repository = DocumentRepository(root / ".roadmap")

    def terminate(stage: str, _path: Path | None) -> None:
        if stage == checkpoint:
            os.kill(os.getpid(), signal.SIGKILL)

    if operation == "migration":
        projection = SQLiteProjection(root / ".roadmap/db/projection.db", repository)
        migration = FilesystemWorkspaceMigration(
            root / ".roadmap",
            projection,
            root / "personal/config.yaml",
            failure_injector=terminate,
        )
        migration.execute(migration.preflight().fingerprint)
        return
    with CanonicalUnitOfWork(
        repository, timeout=0.1, failure_injector=terminate
    ) as unit:
        if operation == "hold":
            (root / "writer-ready").write_text("locked")
            time.sleep(30)
            return
        if operation == "recover":
            return
        if operation == "delete":
            assert unit.delete_issue(EntityId("issue-1"))
        else:
            issue = unit.load_issue(EntityId("issue-1"))
            milestone = unit.load_milestone(EntityId("milestone-1"))
            assert issue is not None and milestone is not None
            now = Timestamp(datetime.now(UTC))
            unit.save_issue(issue.rename(Title("Recovered issue"), now))
            unit.save_milestone(milestone.rename(Name("Recovered milestone"), now))
        unit.commit()


if __name__ == "__main__":
    main()
