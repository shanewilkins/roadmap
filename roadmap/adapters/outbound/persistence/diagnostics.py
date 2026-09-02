"""Read-only workspace diagnosis and bounded derived-state recovery."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from roadmap.application.contracts import (
    HealthFinding,
    HealthReport,
    HealthSeverity,
    RepairAction,
)
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.domain.aggregates import Issue, Milestone, Project

from .canonical import CanonicalUnitOfWork, RecoveryError, WorkspaceBusy
from .documents import DocumentEnvelope, DocumentRepository, parse_document
from .projection import SQLiteProjection


class FilesystemWorkspaceDiagnostics:
    """Diagnose canonical files without treating SQLite as authority."""

    _KINDS = ("project", "milestone", "issue")

    def __init__(
        self,
        repository: DocumentRepository,
        projection: SQLiteProjection,
    ) -> None:
        self._repository = repository
        self._projection = projection
        self._roadmap_dir = repository.roadmap_dir

    def scan(self) -> HealthReport:
        findings: list[HealthFinding] = []
        envelopes = self._canonical_findings(findings)
        if envelopes is not None:
            self._relationship_findings(envelopes, findings)
            try:
                state = self._projection.inspect_state()
            except (OSError, sqlite3.Error) as error:
                findings.append(
                    HealthFinding(
                        "projection.unreadable",
                        HealthSeverity.ERROR,
                        "projection",
                        f"SQLite projection cannot be inspected: {type(error).__name__}",
                    )
                )
                state = "current"
            if state != "current":
                findings.append(
                    HealthFinding(
                        "projection.not-current",
                        HealthSeverity.WARNING,
                        "projection",
                        f"SQLite projection is {state}; canonical files remain authoritative",
                        safe_action="projection",
                    )
                )
        pending = self._pending_transactions(findings)
        if pending:
            findings.append(
                HealthFinding(
                    "transaction.interrupted",
                    HealthSeverity.ERROR,
                    "workspace",
                    f"{len(pending)} interrupted canonical transaction(s) require recovery",
                    safe_action="recovery",
                )
            )
        return HealthReport(tuple(sorted(findings, key=self._finding_key)))

    def preview(self, repair_type: str) -> tuple[RepairAction, ...]:
        actions: list[RepairAction] = []
        if repair_type in {"all", "recovery", "data_integrity"}:
            pending = self._pending_transactions()
            if pending:
                actions.append(
                    RepairAction(
                        "recover-interrupted-transactions",
                        "Recover interrupted canonical transactions from their durable journals",
                        pending,
                    )
                )
        if repair_type in {"all", "projection", "data_integrity"}:
            report = self.scan()
            blocked = any(
                (
                    finding.finding_id.startswith("canonical.")
                    or finding.finding_id == "projection.unreadable"
                )
                and finding.severity in {HealthSeverity.ERROR, HealthSeverity.CRITICAL}
                for finding in report.findings
            )
            state = (
                "blocked-by-canonical-errors"
                if blocked
                else self._projection.inspect_state()
            )
            if state not in {"current", "blocked-by-canonical-errors"}:
                actions.append(
                    RepairAction(
                        "rebuild-projection",
                        f"Rebuild the {state} SQLite projection from canonical files",
                        ("db/projection.db",),
                    )
                )
        return tuple(actions)

    def apply(self, actions: tuple[RepairAction, ...]) -> None:
        try:
            for action in actions:
                if action.action_id == "recover-interrupted-transactions":
                    with CanonicalUnitOfWork(self._repository, self._projection):
                        pass
                elif action.action_id == "rebuild-projection":
                    self._projection.rebuild()
                else:
                    raise ValueError(f"unknown repair action: {action.action_id}")
        except (OSError, sqlite3.Error, RecoveryError, WorkspaceBusy) as error:
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE,
                f"Workspace repair failed: {error}",
            ) from error

    def _process_document(
        self,
        path: Path,
        kind: str,
        findings: list[HealthFinding],
        identities: set[tuple[str, str]],
    ) -> tuple[DocumentEnvelope | None, bool]:
        relative = path.relative_to(self._roadmap_dir).as_posix()
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            findings.append(
                HealthFinding(
                    "canonical.unreadable",
                    HealthSeverity.CRITICAL,
                    relative,
                    f"Canonical document cannot be read: {type(error).__name__}",
                )
            )
            return None, False
        if all(marker in content for marker in ("<<<<<<<", "=======", ">>>>>>>")):
            findings.append(
                HealthFinding(
                    "canonical.git-conflict",
                    HealthSeverity.CRITICAL,
                    relative,
                    "Canonical document contains unresolved Git conflict markers",
                )
            )
            return None, False
        try:
            envelope = parse_document(path, kind)  # type: ignore[arg-type, ty:invalid-argument-type]
        except Exception as error:
            findings.append(
                HealthFinding(
                    "canonical.invalid",
                    HealthSeverity.CRITICAL,
                    relative,
                    f"Canonical document is invalid: {error}",
                )
            )
            return None, False
        key = (kind, envelope.identity)
        if key in identities:
            findings.append(
                HealthFinding(
                    "canonical.duplicate-id",
                    HealthSeverity.CRITICAL,
                    relative,
                    f"Duplicate {kind} identity {envelope.identity}",
                    envelope.identity,
                )
            )
            return None, False
        identities.add(key)
        expected = self._repository.default_path(kind, envelope.aggregate)  # type: ignore[arg-type, ty:invalid-argument-type]
        if path != expected:
            findings.append(
                HealthFinding(
                    "canonical.noncanonical-path",
                    HealthSeverity.ERROR,
                    relative,
                    f"{kind.title()} {envelope.identity} is not stored at its stable-ID path",
                    envelope.identity,
                )
            )
        return envelope, True

    def _kind_findings(
        self,
        kind: str,
        findings: list[HealthFinding],
        identities: set[tuple[str, str]],
    ) -> tuple[list[DocumentEnvelope], bool]:
        directory = self._roadmap_dir / f"{kind}s"
        try:
            paths = sorted(directory.glob("**/*.md"))
        except OSError as error:
            findings.append(
                HealthFinding(
                    "canonical.unreadable",
                    HealthSeverity.CRITICAL,
                    directory.relative_to(self._roadmap_dir).as_posix(),
                    f"Canonical directory cannot be read: {type(error).__name__}",
                )
            )
            return [], False
        envelopes: list[DocumentEnvelope] = []
        healthy = True
        for path in paths:
            envelope, ok = self._process_document(path, kind, findings, identities)
            healthy = healthy and ok
            if envelope is not None:
                envelopes.append(envelope)
        return envelopes, healthy

    def _canonical_findings(
        self, findings: list[HealthFinding]
    ) -> list[DocumentEnvelope] | None:
        envelopes: list[DocumentEnvelope] = []
        identities: set[tuple[str, str]] = set()
        healthy = True
        for kind in self._KINDS:
            kind_envelopes, kind_healthy = self._kind_findings(
                kind, findings, identities
            )
            envelopes.extend(kind_envelopes)
            healthy = healthy and kind_healthy
        return envelopes if healthy else None

    @staticmethod
    def _references_for(
        aggregate,
        issue_ids: set[str],
        milestone_ids: set[str],
        project_ids: set[str],
    ) -> list[tuple[str, set[str]]]:
        if isinstance(aggregate, Issue):
            references = [
                (str(identity), issue_ids)
                for identity in (
                    *aggregate.relations.depends_on,
                    *aggregate.relations.blocks,
                )
            ]
            if aggregate.relations.milestone_id is not None:
                references.append(
                    (str(aggregate.relations.milestone_id), milestone_ids)
                )
            return references
        if isinstance(aggregate, Milestone):
            if aggregate.relation.project_id is not None:
                return [(str(aggregate.relation.project_id), project_ids)]
            return []
        if isinstance(aggregate, Project):
            return [
                (str(identity), milestone_ids)
                for identity in aggregate.relations.milestone_ids
            ]
        return []

    @staticmethod
    def _append_broken_reference_findings(
        envelope: DocumentEnvelope,
        references: list[tuple[str, set[str]]],
        findings: list[HealthFinding],
    ) -> None:
        for missing in sorted(
            identity for identity, valid_ids in references if identity not in valid_ids
        ):
            findings.append(
                HealthFinding(
                    "canonical.broken-reference",
                    HealthSeverity.ERROR,
                    envelope.path.name,
                    f"Entity {envelope.identity} references missing entity {missing}",
                    envelope.identity,
                )
            )

    @classmethod
    def _relationship_findings(
        cls, envelopes: list[DocumentEnvelope], findings: list[HealthFinding]
    ) -> None:
        issue_ids = {
            str(item.aggregate.id)
            for item in envelopes
            if isinstance(item.aggregate, Issue)
        }
        milestone_ids = {
            str(item.aggregate.id)
            for item in envelopes
            if isinstance(item.aggregate, Milestone)
        }
        project_ids = {
            str(item.aggregate.id)
            for item in envelopes
            if isinstance(item.aggregate, Project)
        }
        for envelope in envelopes:
            references = cls._references_for(
                envelope.aggregate, issue_ids, milestone_ids, project_ids
            )
            cls._append_broken_reference_findings(envelope, references, findings)

    def _pending_transactions(
        self, findings: list[HealthFinding] | None = None
    ) -> tuple[str, ...]:
        root = self._roadmap_dir / "db" / "transactions"
        try:
            if not root.exists():
                return ()
            return tuple(
                f"db/transactions/{path.name}"
                for path in sorted(root.iterdir())
                if path.is_dir()
            )
        except OSError as error:
            if findings is not None:
                findings.append(
                    HealthFinding(
                        "transaction.unreadable",
                        HealthSeverity.CRITICAL,
                        "db/transactions",
                        f"Transaction journals cannot be read: {type(error).__name__}",
                    )
                )
            return ()

    @staticmethod
    def _finding_key(finding: HealthFinding) -> tuple[str, str, str]:
        return finding.severity.value, finding.finding_id, finding.scope
