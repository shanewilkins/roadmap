"""Worked governance examples: complete, failed, stale and renewed evidence."""

from dataclasses import replace

import pytest

from roadmap.domain.failures import DomainFailure
from roadmap.domain.requirement_governance import EvidenceResult
from roadmap.domain.requirements import RequirementStatus as Status
from roadmap.domain.types import EntityId
from tests.unit.domain.test_requirements import NOW, requirement


def accept(value=None):
    return (value or requirement()).transition(
        Status.ACCEPTED, NOW, "Alice", "Reviewed criteria"
    )


def prove(value, criterion="C1", result=EvidenceResult.PASS):
    return value.add_evidence(criterion, result, "commit:abc123", NOW, "Bob")


def verified():
    return prove(prove(accept()), "C2").transition(
        Status.VERIFIED, NOW, "Alice", "All criteria met"
    )


def test_verification_requires_acceptance_and_latest_pass_for_every_criterion():
    original = requirement()
    with pytest.raises(DomainFailure):
        original.transition(Status.VERIFIED, NOW, "Alice", "Skip acceptance")
    with pytest.raises(DomainFailure):
        prove(original)
    value = prove(accept())
    assert value.verification == {"C1": "pass", "C2": "missing"}
    with pytest.raises(DomainFailure):
        value.transition(Status.VERIFIED, NOW, "Alice", "Partial")
    value = prove(value, "C2", EvidenceResult.INCOMPLETE)
    with pytest.raises(DomainFailure):
        value.transition(Status.VERIFIED, NOW, "Alice", "Incomplete")
    value = prove(value, "C2")
    assert value.status is Status.ACCEPTED
    assert (
        value.transition(Status.VERIFIED, NOW, "Alice", "Complete").status
        is Status.VERIFIED
    )


def test_latest_failure_demotes_verified_and_pass_needs_explicit_reverification():
    value = prove(verified(), result=EvidenceResult.FAIL)
    assert value.status is Status.IN_PROGRESS
    with pytest.raises(DomainFailure):
        value.transition(Status.VERIFIED, NOW, "Alice", "Failed")
    value = prove(value)
    assert value.status is Status.IN_PROGRESS
    assert len(value.evidence) == 4
    assert (
        value.transition(Status.VERIFIED, NOW, "Alice", "Retry passed").status
        is Status.VERIFIED
    )


def test_reacceptance_at_same_digest_requires_new_evidence():
    original = verified()
    renewed = accept(original)
    assert renewed.current_revision == original.current_revision
    assert renewed.active_acceptance_id != original.active_acceptance_id
    assert renewed.evidence == original.evidence
    assert renewed.verification == {"C1": "missing", "C2": "missing"}
    with pytest.raises(DomainFailure):
        renewed.transition(Status.VERIFIED, NOW, "Alice", "Old results")


def test_manual_intent_change_is_stale_and_metadata_preserves_acceptance():
    original = verified()
    assert replace(original, owner="Carol").effective_status is Status.VERIFIED
    changed = replace(
        original, definition=replace(original.definition, statement="Changed")
    )
    assert changed.effective_status is Status.DRAFT
    assert not changed.acceptance_current
    assert changed.verification == {"C1": "missing", "C2": "missing"}
    with pytest.raises(DomainFailure):
        prove(changed)
    renewed = accept(changed)
    assert len(renewed.revisions) == 2
    assert renewed.evidence == original.evidence
    assert renewed.history[-3].action == "acceptance-stale"


@pytest.mark.parametrize("state", [Status.DEFERRED, Status.REJECTED])
def test_withdrawn_states_return_through_draft(state):
    value = accept().transition(state, NOW, "Alice", "Postponed")
    assert value.active_acceptance_id is None
    with pytest.raises(DomainFailure):
        accept(value)
    draft = value.transition(Status.DRAFT, NOW, "Alice", "Reconsider")
    assert accept(draft).acceptance_current


def test_invalid_governance_cannot_be_constructed():
    value = accept()
    for action in (
        lambda: value.transition(Status.ACCEPTED, NOW, "Alice", "Same state"),
        lambda: value.transition(Status.IN_PROGRESS, NOW, "Alice", " "),
        lambda: value.add_evidence("missing", EvidenceResult.PASS, "sha", NOW, "Bob"),
        lambda: value.add_evidence("C1", EvidenceResult.PASS, " ", NOW, "Bob"),
        lambda: replace(requirement(), status=Status.VERIFIED),
        lambda: replace(value, status=Status.VERIFIED),
        lambda: replace(value, acceptances=(*value.acceptances, *value.acceptances)),
        lambda: replace(
            prove(value),
            evidence=(replace(prove(value).evidence[0], revision="0" * 64),),
        ),
    ):
        with pytest.raises(DomainFailure):
            action()


def test_governance_record_identity_and_attribution_cannot_be_blank_or_malformed():
    value = prove(accept())
    acceptance, entry = value.acceptances[0], value.evidence[0]
    for changes in (
        {"id": EntityId("bad-uuid")},
        {"id": EntityId("00000000-0000-1000-8000-000000000001")},
        {"actor": " "},
        {"revision": "not-a-digest"},
        {"reason": " "},
    ):
        with pytest.raises(DomainFailure):
            replace(acceptance, **changes)
    with pytest.raises(DomainFailure):
        replace(entry, result="unsupported")


def test_historical_governance_references_must_resolve_to_accepted_definitions():
    value = prove(accept())
    original_acceptance = value.acceptances[0]
    renewed = accept(value.transition(Status.IN_PROGRESS, NOW, "Alice", "Started"))
    for action in (
        lambda: replace(value, revisions=()),
        lambda: replace(
            value, evidence=(replace(value.evidence[0], criterion="missing"),)
        ),
        lambda: replace(requirement(), active_acceptance_id=EntityId.new()),
        lambda: replace(renewed, active_acceptance_id=original_acceptance.id),
    ):
        with pytest.raises(DomainFailure):
            action()
