"""Stub Domain value for the planned Requirements entity (TR-045 fixture)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RequirementId:
    """Fixture identity for a requirement artifact."""

    value: str
