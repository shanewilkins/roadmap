"""Stub Application use case for the planned Requirements entity (TR-045 fixture)."""

from dataclasses import dataclass

from roadmap.domain.requirements import RequirementId


@dataclass(frozen=True)
class CreateRequirementRequest:
    """Fixture use-case request."""

    id_value: str


def execute(request: CreateRequirementRequest) -> RequirementId:
    """Map a fixture request to a Domain identity."""
    return RequirementId(request.id_value)
