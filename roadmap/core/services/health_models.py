"""Shared health scanning models.

Holds dataclasses and enums used by the various health scanners.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    """Types of entities that can be scanned."""

    ISSUE = "issue"
    MILESTONE = "milestone"
    PROJECT = "project"


class HealthSeverity(str, Enum):
    """Severity levels for health issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthIssue:
    """A single health issue found during scanning."""

    code: str
    message: str
    severity: HealthSeverity
    category: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityHealthReport:
    """Health report for a single entity."""

    entity_id: str
    entity_type: EntityType
    entity_title: str
    status: str
    issues: list[HealthIssue] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == HealthSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == HealthSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == HealthSeverity.INFO)

    @property
    def is_healthy(self) -> bool:
        return not any(
            i.severity in (HealthSeverity.ERROR, HealthSeverity.CRITICAL)
            for i in self.issues
        )

    @property
    def is_degraded(self) -> bool:
        return any(i.severity == HealthSeverity.WARNING for i in self.issues)
