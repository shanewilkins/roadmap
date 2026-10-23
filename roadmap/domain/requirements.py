"""Pure optional requirement identity and acceptance-bearing definitions."""

import json
import re
from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from .failures import InvalidTransition, InvalidValue, InvariantViolation
from .requirement_governance import (
    EvidenceResult,
    RequirementAcceptance,
    RequirementEvidence,
)
from .types import EntityId, Priority, RequiredText, RetentionState, Timestamp


class RequirementKind(StrEnum):
    USER = "user"
    TECHNICAL = "technical"

    @property
    def prefix(self) -> str:
        return "UR" if self is RequirementKind.USER else "TR"


class RequirementStatus(StrEnum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in-progress"
    VERIFIED = "verified"
    DEFERRED = "deferred"
    REJECTED = "rejected"


_ACTIVE = {
    RequirementStatus.ACCEPTED,
    RequirementStatus.IN_PROGRESS,
    RequirementStatus.VERIFIED,
}
_TRANSITIONS = {
    RequirementStatus.DRAFT: {
        RequirementStatus.ACCEPTED,
        RequirementStatus.DEFERRED,
        RequirementStatus.REJECTED,
    },
    RequirementStatus.ACCEPTED: set(RequirementStatus) - {RequirementStatus.ACCEPTED},
    RequirementStatus.IN_PROGRESS: set(RequirementStatus)
    - {RequirementStatus.IN_PROGRESS},
    RequirementStatus.VERIFIED: set(RequirementStatus) - {RequirementStatus.VERIFIED},
    RequirementStatus.DEFERRED: {RequirementStatus.DRAFT},
    RequirementStatus.REJECTED: {RequirementStatus.DRAFT},
}


class RequirementKey(RequiredText):
    """Readable alias, independent of a requirement's UUID identity."""

    def __new__(cls, value: str):
        if not re.fullmatch(r"(?:UR|TR)-(?:[0-9]{3,})", value):
            raise InvalidValue("requirement key must be UR-NNN or TR-NNN")
        number = int(value[3:])
        if number < 1 or value != f"{value[:2]}-{number:03d}":
            raise InvalidValue("requirement key must use a positive canonical number")
        return super().__new__(cls, value)


@dataclass(frozen=True, slots=True)
class RequirementCriterion:
    id: str
    text: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", self.id):
            raise InvalidValue("criterion ID must start with a letter and be path-free")
        if not self.text.strip():
            raise InvalidValue("criterion text cannot be empty")


def _lines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


@dataclass(frozen=True, slots=True)
class RequirementDefinition:
    """Versioned content to which acceptance and evidence can later apply."""

    kind: RequirementKind
    title: RequiredText
    statement: str
    criteria: tuple[RequirementCriterion, ...]
    scope: str = ""

    def __post_init__(self) -> None:
        if not self.statement.strip():
            raise InvalidValue("requirement statement cannot be empty")
        if not self.criteria:
            raise InvalidValue("requirement needs at least one criterion")
        if len({item.id for item in self.criteria}) != len(self.criteria):
            raise InvalidValue("criterion IDs must be unique within a requirement")

    @property
    def fingerprint(self) -> str:
        payload = {
            "contract": "roadmap.requirement.intent:v1",
            "kind": self.kind.value,
            "title": str(self.title),
            "statement": _lines(self.statement),
            "scope": _lines(self.scope),
            "criteria": [
                {"id": item.id, "text": _lines(item.text)}
                for item in sorted(self.criteria, key=lambda item: item.id)
            ],
        }
        encoded = json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class RequirementRevision:
    definition: RequirementDefinition
    at: Timestamp
    actor: str

    def __post_init__(self) -> None:
        if not self.actor.strip():
            raise InvalidValue("requirement revision actor cannot be empty")


@dataclass(frozen=True, slots=True)
class RequirementEvent:
    action: str
    at: Timestamp
    actor: str
    revision: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.actor.strip() or not self.action.strip():
            raise InvalidValue("requirement history needs action and actor")
        if not re.fullmatch(r"[a-f0-9]{64}", self.revision):
            raise InvalidValue("requirement history needs a valid intent fingerprint")


@dataclass(frozen=True, slots=True)
class Requirement:
    id: EntityId
    created: Timestamp
    updated: Timestamp
    key: RequirementKey
    definition: RequirementDefinition
    rationale: str = ""
    priority: Priority = Priority.MEDIUM
    owner: str | None = None
    journey: str | None = None
    stage: str | None = None
    revisions: tuple[RequirementRevision, ...] = ()
    history: tuple[RequirementEvent, ...] = ()
    status: RequirementStatus = RequirementStatus.DRAFT
    retention: RetentionState = RetentionState.VISIBLE
    acceptances: tuple[RequirementAcceptance, ...] = ()
    evidence: tuple[RequirementEvidence, ...] = ()
    active_acceptance_id: EntityId | None = None

    def __post_init__(self) -> None:
        try:
            identity = UUID(str(self.id))
        except ValueError as error:
            raise InvalidValue("requirement ID must be a complete UUID4") from error
        if identity.version != 4 or str(identity) != str(self.id):
            raise InvalidValue("requirement ID must be a complete canonical UUID4")
        if not self.key.startswith(self.definition.kind.prefix + "-"):
            raise InvalidValue("requirement key prefix must match its type")
        if self.updated < self.created:
            raise InvariantViolation("updated cannot precede requirement creation")
        if self.owner is not None and not self.owner.strip():
            raise InvalidValue("requirement owner must be non-empty or unset")
        self._validate_governance()

    def _validate_governance(self) -> None:
        acceptances = {item.id: item for item in self.acceptances}
        identities = [x.id for x in (*self.acceptances, *self.evidence)]
        if len(set(identities)) != len(identities):
            raise InvariantViolation("governance record IDs must be unique")
        definitions = {x.definition.fingerprint: x.definition for x in self.revisions}
        for acceptance in self.acceptances:
            if acceptance.revision not in definitions or acceptance.at < self.created:
                raise InvariantViolation(
                    "acceptance must name a captured intent revision"
                )
        self._validate_evidence(acceptances, definitions)
        self._validate_active_acceptance(acceptances, definitions)

    def _validate_evidence(self, acceptances, definitions) -> None:
        for entry in self.evidence:
            acceptance = acceptances.get(entry.acceptance_id)
            if acceptance is None or entry.revision != acceptance.revision:
                raise InvariantViolation("evidence must name its acceptance revision")
            criterion_ids = {x.id for x in definitions[acceptance.revision].criteria}
            if entry.criterion not in criterion_ids or entry.at < acceptance.at:
                raise InvariantViolation(
                    "evidence must name an accepted criterion and date"
                )

    def _validate_active_acceptance(self, acceptances, definitions) -> None:
        active = acceptances.get(self.active_acceptance_id)
        if (self.status in _ACTIVE) != (active is not None):
            raise InvariantViolation(
                "active requirement state requires active acceptance"
            )
        if self.active_acceptance_id is not None and active is None:
            raise InvariantViolation("unknown active acceptance")
        if active and active != self.acceptances[-1]:
            raise InvariantViolation("only the latest acceptance can be active")
        if self.status is RequirementStatus.VERIFIED and active:
            definition = definitions[active.revision]
            if not self._passing(definition):
                raise InvariantViolation(
                    "Verified requires passing evidence for every criterion"
                )

    @property
    def acceptance_current(self) -> bool:
        return bool(
            self.active_acceptance_id
            and self.acceptances[-1].revision == self.current_revision
        )

    @property
    def effective_status(self) -> RequirementStatus:
        if self.status in _ACTIVE and not self.acceptance_current:
            return RequirementStatus.DRAFT
        return self.status

    def _latest_evidence(self) -> dict[str, RequirementEvidence]:
        return {
            entry.criterion: entry
            for entry in self.evidence
            if entry.acceptance_id == self.active_acceptance_id
        }

    def _passing(self, definition: RequirementDefinition) -> bool:
        latest = self._latest_evidence()
        return all(
            item.id in latest and latest[item.id].result is EvidenceResult.PASS
            for item in definition.criteria
        )

    @property
    def verification(self) -> dict[str, str]:
        latest = self._latest_evidence() if self.acceptance_current else {}
        return {
            item.id: latest[item.id].result.value if item.id in latest else "missing"
            for item in self.definition.criteria
        }

    def withdraw_stale_acceptance(self, at: Timestamp, actor: str) -> "Requirement":
        if self.status not in _ACTIVE or self.acceptance_current:
            return self
        return replace(
            self, status=RequirementStatus.DRAFT, active_acceptance_id=None
        ).record(
            "acceptance-stale", at, actor, "Intent changed; renewed acceptance required"
        )

    def transition(
        self, status: RequirementStatus, at: Timestamp, actor: str, reason: str
    ) -> "Requirement":
        if not reason.strip():
            raise InvalidValue("transition needs a nonempty reason")
        value = self.withdraw_stale_acceptance(at, actor)
        if status not in _TRANSITIONS[value.status]:
            raise InvalidTransition(
                f"Cannot transition requirement {value.status} -> {status}"
            )
        if status is RequirementStatus.VERIFIED and not value._passing(
            value.definition
        ):
            raise InvalidTransition(
                "Verification requires latest passing evidence for every criterion"
            )
        acceptances, active = value.acceptances, value.active_acceptance_id
        if status is RequirementStatus.ACCEPTED:
            value = value.record("intent-reviewed", at, actor)
            acceptance = RequirementAcceptance(
                EntityId.new(), value.current_revision, at, actor, reason
            )
            acceptances, active = (*acceptances, acceptance), acceptance.id
        elif status not in _ACTIVE:
            active = None
        return replace(
            value, status=status, acceptances=acceptances, active_acceptance_id=active
        ).record(f"status:{status}", at, actor, reason)

    def add_evidence(
        self,
        criterion: str,
        result: EvidenceResult,
        reference: str,
        at: Timestamp,
        actor: str,
        note: str = "",
    ) -> "Requirement":
        if not self.acceptance_current or self.status not in _ACTIVE:
            raise InvalidTransition(
                "Evidence requires active acceptance of current intent"
            )
        if criterion not in {item.id for item in self.definition.criteria}:
            raise InvalidValue(f"Unknown requirement criterion: {criterion}")
        assert self.active_acceptance_id is not None
        entry = RequirementEvidence(
            EntityId.new(),
            self.active_acceptance_id,
            self.current_revision,
            criterion,
            result,
            reference,
            at,
            actor,
            note,
        )
        status = self.status
        if status is RequirementStatus.VERIFIED and result is not EvidenceResult.PASS:
            status = RequirementStatus.IN_PROGRESS
        return replace(self, evidence=(*self.evidence, entry), status=status).record(
            f"evidence:{result}", at, actor, note or reference
        )

    @property
    def content(self) -> str:
        return self.definition.statement

    @property
    def current_revision(self) -> str:
        # Recompute from actual content, including manual edits. A stored
        # fingerprint is never sufficient evidence of current intent.
        return self.definition.fingerprint

    @property
    def uncaptured_intent(self) -> bool:
        return not any(
            item.definition.fingerprint == self.current_revision
            for item in self.revisions
        )

    def record(
        self, action: str, at: Timestamp, actor: str, reason: str | None = None
    ) -> "Requirement":
        revisions = self.revisions
        if self.uncaptured_intent:
            revisions = (*revisions, RequirementRevision(self.definition, at, actor))
        event = RequirementEvent(action, at, actor, self.current_revision, reason)
        return replace(
            self, updated=at, revisions=revisions, history=(*self.history, event)
        )

    def rekey(self, key: RequirementKey, at: Timestamp, actor: str) -> "Requirement":
        changed = replace(self, key=key)
        return changed.record("rekeyed", at, actor, f"{self.key} -> {key}")
