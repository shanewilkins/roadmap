"""Immutable acceptance and criterion evidence values; no storage dependencies."""

import re
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from .failures import InvalidValue
from .types import EntityId, Timestamp


class EvidenceResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"


def _identity(value: EntityId) -> None:
    try:
        identity = UUID(str(value))
    except ValueError as error:
        raise InvalidValue("governance record needs a complete UUID4") from error
    if identity.version != 4 or str(identity) != str(value):
        raise InvalidValue("governance record needs a canonical UUID4")


def _attribution(identity: EntityId, revision: str, actor: str) -> None:
    _identity(identity)
    if not re.fullmatch(r"[a-f0-9]{64}", revision) or not actor.strip():
        raise InvalidValue("governance record needs intent fingerprint and actor")


@dataclass(frozen=True, slots=True)
class RequirementAcceptance:
    id: EntityId
    revision: str
    at: Timestamp
    actor: str
    reason: str

    def __post_init__(self) -> None:
        _attribution(self.id, self.revision, self.actor)
        if not self.reason.strip():
            raise InvalidValue("acceptance needs a nonempty reason")


@dataclass(frozen=True, slots=True)
class RequirementEvidence:
    id: EntityId
    acceptance_id: EntityId
    revision: str
    criterion: str
    result: EvidenceResult
    reference: str
    at: Timestamp
    actor: str
    note: str = ""

    def __post_init__(self) -> None:
        _attribution(self.id, self.revision, self.actor)
        _identity(self.acceptance_id)
        if not self.criterion.strip() or not self.reference.strip():
            raise InvalidValue("evidence needs criterion and commit/artifact reference")
        if not isinstance(self.result, EvidenceResult):
            raise InvalidValue("evidence result must be pass, fail or incomplete")
