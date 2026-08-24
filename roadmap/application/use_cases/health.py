"""Workspace diagnosis and explicitly bounded repair."""

from roadmap.application.contracts import HealthReport, RepairResult
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import WorkspaceDiagnosticsPort


class WorkspaceHealth:
    """Separate non-mutating detection from confirmed recovery."""

    _REPAIR_TYPES = {"all", "projection", "recovery", "data_integrity"}

    def __init__(self, diagnostics: WorkspaceDiagnosticsPort):
        self._diagnostics = diagnostics

    def scan(self) -> HealthReport:
        return self._diagnostics.scan()

    def repair(self, repair_type: str, *, dry_run: bool) -> RepairResult:
        normalized = repair_type.casefold()
        if normalized not in self._REPAIR_TYPES:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST,
                f"Fix type '{repair_type}' has no safe 0.2 repair; inspect the finding and edit canonical files explicitly",
            )
        actions = self._diagnostics.preview(normalized)
        if not dry_run and actions:
            self._diagnostics.apply(actions)
        return RepairResult(dry_run, actions, self._diagnostics.scan())
