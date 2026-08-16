"""Valid Application DTO."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    """Fixture use-case request."""

    work_id: str
