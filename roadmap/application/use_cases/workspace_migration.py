"""Explicit workspace migration use case."""

from roadmap.application.contracts import MigrationPlan, MigrationResult
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import WorkspaceMigrationPort


class WorkspaceMigration:
    """Coordinate the single supported 0.1.1-to-0.2 workspace migration."""

    def __init__(self, migration: WorkspaceMigrationPort):
        self._migration = migration

    def preflight(self) -> MigrationPlan:
        return self._migration.preflight()

    def execute(self, fingerprint: str) -> MigrationResult:
        plan = self._migration.preflight()
        if plan.conflicts:
            raise ApplicationFailure(
                FailureCategory.CONFLICT,
                "Migration cannot proceed: " + "; ".join(plan.conflicts),
            )
        if plan.fingerprint != fingerprint:
            raise ApplicationFailure(
                FailureCategory.CONFLICT,
                "Workspace changed after migration preflight; run the dry-run again.",
            )
        return self._migration.execute(fingerprint)
