"""Valid pure Domain value."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkId:
    """Fixture identity."""

    value: str
