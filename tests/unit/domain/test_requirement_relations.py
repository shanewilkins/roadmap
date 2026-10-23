"""Typed requirement relation invariants and governance independence."""

from dataclasses import replace

import pytest

from roadmap.domain.failures import DomainFailure
from roadmap.domain.requirement_relations import RequirementRelationKind
from roadmap.domain.types import EntityId
from tests.unit.domain.test_requirement_governance import accept, prove
from tests.unit.domain.test_requirements import NOW, requirement


def test_relation_changes_preserve_intent_revision_and_governance():
    original = requirement()
    linked = original.link(
        RequirementRelationKind.IMPLEMENTED_BY,
        "issue-1",
        NOW,
        "Alice",
    )
    assert linked.current_revision == original.current_revision
    assert linked.revisions == original.revisions
    assert linked.relations.implemented_by == (EntityId("issue-1"),)
    assert linked.history[-1].action == "relation:implemented-by:linked"
    assert (
        linked.unlink(
            RequirementRelationKind.IMPLEMENTED_BY, "issue-1", NOW, "Alice"
        ).relations.implemented_by
        == ()
    )


def test_report_links_are_attributed_and_repository_qualified():
    linked = requirement().link(
        RequirementRelationKind.REPORT,
        "https://github.com/acme/widgets/issues/42",
        NOW,
        "Alice",
    )
    [report] = linked.relations.reports
    assert report.actor == "Alice" and report.at == NOW
    with pytest.raises(DomainFailure):
        requirement().link(
            RequirementRelationKind.REPORT, "https://example.com", NOW, "Alice"
        )


def test_duplicate_self_cardinality_and_derived_evidence_links_refuse():
    original = requirement()
    for action in (
        lambda: original.link(
            RequirementRelationKind.DEPENDS_ON, str(original.id), NOW, "Alice"
        ),
        lambda: replace(
            original,
            relations=replace(
                original.relations,
                implemented_by=(EntityId("issue-1"), EntityId("issue-1")),
            ),
        ),
        lambda: original.link(
            RequirementRelationKind.EVIDENCE, "evidence-1", NOW, "Alice"
        ),
        lambda: original.link(
            RequirementRelationKind.PROJECT_TARGET, "project-1", NOW, "Alice"
        ).link(RequirementRelationKind.PROJECT_TARGET, "project-2", NOW, "Alice"),
    ):
        with pytest.raises(DomainFailure):
            action()


def test_evidence_relations_are_derived_from_immutable_history():
    value = prove(accept())
    assert value.relation_targets(RequirementRelationKind.EVIDENCE) == (
        str(value.evidence[0].id),
    )
