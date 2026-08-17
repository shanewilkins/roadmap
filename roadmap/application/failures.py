"""Stable failure categories exposed by application use cases."""

from dataclasses import dataclass
from enum import StrEnum


class FailureCategory(StrEnum):
    NOT_FOUND = "not-found"
    CONFLICT = "conflict"
    INVALID_REQUEST = "invalid-request"
    STORAGE_UNAVAILABLE = "storage-unavailable"
    PROJECTION_STALE = "projection-stale"


@dataclass(frozen=True, slots=True)
class ApplicationFailure(Exception):
    category: FailureCategory
    message: str

    def __str__(self) -> str:
        return self.message
