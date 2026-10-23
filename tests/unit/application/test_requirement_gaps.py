"""Exact requirement gap populations and reasons."""

from dataclasses import replace
from uuid import uuid4

from roadmap.application.use_cases.requirement_gaps import calculate_requirement_gaps
from roadmap.domain.aggregates import Issue
from roadmap.domain.requirement_governance import EvidenceResult
from roadmap.domain.requirement_relations import RequirementRelations
from roadmap.domain.requirements import RequirementStatus
from roadmap.domain.types import EntityId, IssueStatus, RetentionState, Title
from tests.unit.domain.test_requirement_governance import accept, prove, verified
from tests.unit.domain.test_requirements import NOW, requirement


def issue(identity: str, *, status=IssueStatus.TODO, **changes):
    return Issue(
        EntityId(identity), NOW, NOW, title=Title(identity), status=status, **changes
    )


def report(requirements, issues=()):
    return calculate_requirement_gaps(tuple(requirements), tuple(issues), (), ())


def test_unplanned_unjustified_maintenance_and_completed_populations():
    unplanned = accept()
    closed = issue("closed", status=IssueStatus.CLOSED, labels=("release:0.4.0",))
    awaiting = replace(
        accept(replace(requirement(), id=EntityId(str(uuid4())))),
        journey="J-10",
        relations=RequirementRelations(implemented_by=(closed.id,)),
    )
    completed = replace(
        verified(),
        id=EntityId(str(uuid4())),
        relations=RequirementRelations(implemented_by=(closed.id,)),
    )
    orphan = issue("orphan")
    maintenance = issue(
        "maintenance",
        labels=("maintenance",),
        content="Upgrade the build image without product behavior changes.",
    )
    result = report(
        (unplanned, awaiting, completed),
        (closed, orphan, maintenance),
    )
    assert [item.entity_id for item in result.accepted_unplanned] == [str(unplanned.id)]
    assert [item.entity_id for item in result.unjustified_work] == ["orphan"]
    assert [item.entity_id for item in result.implemented_awaiting_verification] == [
        str(awaiting.id)
    ]
    release = next(
        group
        for group in result.groups
        if (group.dimension, group.value) == ("release", "0.4.0")
    )
    awaiting_group = next(
        category
        for category in release.categories
        if category.name == "implemented_awaiting_verification"
    )
    assert awaiting_group.entity_ids == (str(awaiting.id),)
    assert release.counts["implemented_awaiting_verification"] == 1


def test_stale_failed_broken_and_blocked_populations():
    dependency = accept()
    blocked_issue = issue("blocked", status=IssueStatus.BLOCKED)
    current = replace(
        accept(replace(requirement(), id=EntityId(str(uuid4())))),
        relations=RequirementRelations(
            depends_on=(dependency.id,),
            implemented_by=(blocked_issue.id, EntityId("missing-issue")),
        ),
    )
    failed = prove(
        accept(replace(requirement(), id=EntityId(str(uuid4())))),
        result=EvidenceResult.FAIL,
    )
    stale_source = prove(accept(replace(requirement(), id=EntityId(str(uuid4())))))
    stale = replace(
        stale_source,
        definition=replace(stale_source.definition, statement="Changed intent"),
    )
    result = report((dependency, current, failed, stale), (blocked_issue,))
    assert [item.entity_id for item in result.failed_evidence] == [str(failed.id)]
    assert [item.entity_id for item in result.stale_evidence] == [str(stale.id)]
    assert result.broken_links[0].entity_id == str(current.id)
    assert result.broken_links[0].reasons == ("implemented-by:missing-issue",)
    [blocked] = [
        item
        for item in result.blocked_requirements
        if item.entity_id == str(current.id)
    ]
    assert any("dependency" in reason for reason in blocked.reasons)
    assert any("blocked" in reason for reason in blocked.reasons)
    assert current.effective_status is RequirementStatus.ACCEPTED


def test_archived_work_does_not_complete_or_break_visible_requirement():
    archived = issue(
        "archived",
        status=IssueStatus.CLOSED,
        retention=RetentionState.ARCHIVED,
    )
    governed = replace(
        accept(),
        relations=RequirementRelations(implemented_by=(archived.id,)),
    )
    result = report((governed,), (archived,))
    assert [item.entity_id for item in result.accepted_unplanned] == [str(governed.id)]
    assert result.implemented_awaiting_verification == ()
    assert result.broken_links == ()


def test_deferred_acceptance_is_not_governed_and_its_evidence_is_stale():
    evidenced = prove(accept())
    deferred = evidenced.transition(
        RequirementStatus.DEFERRED,
        NOW,
        "reviewer",
        "No longer in current scope",
    )
    result = report((deferred,))
    assert result.accepted_unplanned == ()
    assert [item.entity_id for item in result.stale_evidence] == [str(deferred.id)]


def test_archived_requirement_target_is_resolvable_not_broken():
    archived = replace(requirement(), retention=RetentionState.ARCHIVED)
    source = replace(
        requirement(),
        id=EntityId(str(uuid4())),
        relations=RequirementRelations(depends_on=(archived.id,)),
    )
    assert report((source, archived)).broken_links == ()


def test_maintenance_exemption_requires_exact_label_and_nonempty_body():
    wrong_case = issue("wrong-case", labels=("Maintenance",), content="Rationale")
    missing_body = issue("missing-body", labels=("maintenance",), content=" \n")
    result = report((), (wrong_case, missing_body))
    assert [item.entity_id for item in result.unjustified_work] == [
        "missing-body",
        "wrong-case",
    ]
