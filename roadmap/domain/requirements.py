"""Pure optional requirement identity and acceptance-bearing definitions."""

import json
import re
from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from .failures import InvalidValue, InvariantViolation
from .types import EntityId, Priority, RequiredText, RetentionState, Timestamp


class RequirementKind(StrEnum):
    USER = "user"
    TECHNICAL = "technical"

    @property
    def prefix(self) -> str:
        return "UR" if self is RequirementKind.USER else "TR"


class RequirementStatus(StrEnum):
    DRAFT = "draft"


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
