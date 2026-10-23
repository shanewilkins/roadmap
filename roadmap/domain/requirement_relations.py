"""Typed traceability values owned by requirement artifacts."""

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from .failures import InvalidValue
from .types import EntityId, Timestamp


class RequirementRelationKind(StrEnum):
    SUPPORTS = "supports"
    DEPENDS_ON = "depends-on"
    IMPLEMENTED_BY = "implemented-by"
    PROJECT_TARGET = "project-target"
    MILESTONE_TARGET = "milestone-target"
    EVIDENCE = "evidence"
    REPORT = "report"


@dataclass(frozen=True, slots=True)
class ExternalReportReference:
    url: str
    at: Timestamp
    actor: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        path_parts = tuple(part for part in parsed.path.split("/") if part)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or len(path_parts) < 2
        ):
            raise InvalidValue(
                "external report needs an absolute repository-qualified URL"
            )
        if self.url != self.url.strip() or not self.actor.strip():
            raise InvalidValue("external report needs a canonical URL and actor")


def _unique(name: str, values: tuple[EntityId, ...]) -> None:
    if len(values) != len(set(values)):
        raise InvalidValue(f"{name} requirement relations must be unique")


@dataclass(frozen=True, slots=True)
class RequirementRelations:
    supports: tuple[EntityId, ...] = ()
    depends_on: tuple[EntityId, ...] = ()
    implemented_by: tuple[EntityId, ...] = ()
    project_target: EntityId | None = None
    milestone_target: EntityId | None = None
    reports: tuple[ExternalReportReference, ...] = ()

    def validate_for(self, requirement_id: EntityId) -> None:
        for name, values in (
            ("supports", self.supports),
            ("depends-on", self.depends_on),
            ("implemented-by", self.implemented_by),
        ):
            _unique(name, values)
        if requirement_id in self.supports + self.depends_on:
            raise InvalidValue("requirement relations cannot reference self")
        urls = [item.url for item in self.reports]
        if len(urls) != len(set(urls)):
            raise InvalidValue("external report relations must be unique")
