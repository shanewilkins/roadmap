"""Requirement frontmatter mapping inside the canonical persistence boundary."""

from typing import Any

from roadmap.domain.requirement_governance import (
    EvidenceResult,
    RequirementAcceptance,
    RequirementEvidence,
)
from roadmap.domain.requirement_relations import (
    ExternalReportReference,
    RequirementRelations,
)
from roadmap.domain.requirements import (
    Requirement,
    RequirementCriterion,
    RequirementDefinition,
    RequirementEvent,
    RequirementKey,
    RequirementKind,
    RequirementRevision,
    RequirementStatus,
)
from roadmap.domain.types import EntityId, Priority, RequiredText

from .documents import DocumentError, _base, _enum, _ids, _timestamp


def _records(data: dict[str, Any], field: str) -> list[dict[str, Any]]:
    values = data.pop(field, [])
    if not isinstance(values, list) or any(not isinstance(x, dict) for x in values):
        raise DocumentError(f"{field} must be a list of mappings")
    return values


def definition_fields(value: RequirementDefinition) -> dict[str, Any]:
    return {
        "requirement_type": value.kind.value,
        "title": str(value.title),
        "statement": value.statement,
        "scope": value.scope,
        "criteria": [{"id": item.id, "text": item.text} for item in value.criteria],
    }


def definition(value: dict[str, Any], statement: str) -> RequirementDefinition:
    criteria = value["criteria"]
    if not isinstance(criteria, list) or any(not isinstance(x, dict) for x in criteria):
        raise DocumentError("criteria must be a list of named mappings")
    return RequirementDefinition(
        RequirementKind(value["requirement_type"]),
        RequiredText(value["title"]),
        statement,
        tuple(RequirementCriterion(x["id"], x["text"]) for x in criteria),
        value.get("scope", ""),
    )


def _relations(data: dict[str, Any]) -> RequirementRelations:
    values = data.pop("relations", {})
    if not isinstance(values, dict):
        raise DocumentError("relations must be a mapping")
    reports = values.pop("reports", [])
    if not isinstance(reports, list) or any(
        not isinstance(item, dict) for item in reports
    ):
        raise DocumentError("relation reports must be a list of mappings")
    return RequirementRelations(
        supports=_ids(values.pop("supports", []), "relations supports"),
        depends_on=_ids(values.pop("depends_on", []), "relations depends_on"),
        implemented_by=_ids(
            values.pop("implemented_by", []), "relations implemented_by"
        ),
        project_target=(
            EntityId(values.pop("project_target"))
            if values.get("project_target") is not None
            else values.pop("project_target", None)
        ),
        milestone_target=(
            EntityId(values.pop("milestone_target"))
            if values.get("milestone_target") is not None
            else values.pop("milestone_target", None)
        ),
        reports=tuple(
            ExternalReportReference(
                item["url"],
                _timestamp(item["at"], "external report at"),
                item["actor"],
            )
            for item in reports
        ),
    )


def parse_fields(data: dict[str, Any], body: str, path) -> Requirement:
    try:
        base = _base(data)
        current = definition(data, body)
        for key in (
            "requirement_type",
            "title",
            "criteria",
            "scope",
            "current_revision",
        ):
            data.pop(key, None)
        revisions = tuple(
            RequirementRevision(
                definition(x["definition"], x["definition"]["statement"]),
                _timestamp(x["at"], "revision at"),
                x["actor"],
            )
            for x in data.pop("revisions", [])
        )
        history = tuple(
            RequirementEvent(
                x["action"],
                _timestamp(x["at"], "history at"),
                x["actor"],
                x["revision"],
                x.get("reason"),
            )
            for x in data.pop("history", [])
        )
        return Requirement(
            **base,
            key=RequirementKey(data.pop("key")),
            definition=current,
            rationale=data.pop("rationale", ""),
            priority=_enum(Priority, data.pop("priority", "medium"), "priority"),
            owner=data.pop("owner", None),
            journey=data.pop("journey", None),
            stage=data.pop("stage", None),
            revisions=revisions,
            history=history,
            status=_enum(RequirementStatus, data.pop("status", "draft"), "status"),
            acceptances=tuple(
                RequirementAcceptance(
                    EntityId(x["id"]),
                    x["revision"],
                    _timestamp(x["at"], "acceptance at"),
                    x["actor"],
                    x["reason"],
                )
                for x in _records(data, "acceptances")
            ),
            evidence=tuple(
                RequirementEvidence(
                    EntityId(x["id"]),
                    EntityId(x["acceptance_id"]),
                    x["revision"],
                    x["criterion"],
                    EvidenceResult(x["result"]),
                    x["reference"],
                    _timestamp(x["at"], "evidence at"),
                    x["actor"],
                    x.get("note", ""),
                )
                for x in _records(data, "evidence")
            ),
            active_acceptance_id=(
                EntityId(data.pop("active_acceptance_id"))
                if data.get("active_acceptance_id") is not None
                else data.pop("active_acceptance_id", None)
            ),
            relations=_relations(data),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise DocumentError(f"invalid requirement document {path}: {error}") from error


def serialize_fields(value: Requirement) -> dict[str, Any]:
    fields = definition_fields(value.definition)
    fields.pop("statement")
    fields.update(
        key=str(value.key),
        rationale=value.rationale,
        priority=value.priority.value,
        owner=value.owner,
        journey=value.journey,
        stage=value.stage,
        status=value.status.value,
        current_revision=value.current_revision,
        active_acceptance_id=(
            str(value.active_acceptance_id) if value.active_acceptance_id else None
        ),
        acceptances=[
            {
                "id": str(x.id),
                "revision": x.revision,
                "at": x.at.value.isoformat(),
                "actor": x.actor,
                "reason": x.reason,
            }
            for x in value.acceptances
        ],
        evidence=[
            {
                "id": str(x.id),
                "acceptance_id": str(x.acceptance_id),
                "revision": x.revision,
                "criterion": x.criterion,
                "result": x.result.value,
                "reference": x.reference,
                "at": x.at.value.isoformat(),
                "actor": x.actor,
                "note": x.note,
            }
            for x in value.evidence
        ],
        relations={
            "supports": list(map(str, value.relations.supports)),
            "depends_on": list(map(str, value.relations.depends_on)),
            "implemented_by": list(map(str, value.relations.implemented_by)),
            "project_target": (
                str(value.relations.project_target)
                if value.relations.project_target
                else None
            ),
            "milestone_target": (
                str(value.relations.milestone_target)
                if value.relations.milestone_target
                else None
            ),
            "reports": [
                {
                    "url": item.url,
                    "at": item.at.value.isoformat(),
                    "actor": item.actor,
                }
                for item in value.relations.reports
            ],
        },
        revisions=[
            {
                "definition": definition_fields(x.definition),
                "at": x.at.value.isoformat(),
                "actor": x.actor,
            }
            for x in value.revisions
        ],
        history=[
            {
                "action": x.action,
                "at": x.at.value.isoformat(),
                "actor": x.actor,
                "revision": x.revision,
                "reason": x.reason,
            }
            for x in value.history
        ],
    )
    return fields
