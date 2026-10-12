"""Stable identity and conservative intent-revision contract examples."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from roadmap.domain.failures import InvalidValue
from roadmap.domain.requirements import (
    Requirement,
    RequirementCriterion,
    RequirementDefinition,
    RequirementKey,
    RequirementKind,
)
from roadmap.domain.types import EntityId, Priority, RequiredText, Timestamp

NOW = Timestamp(datetime(2026, 10, 10, tzinfo=UTC))


def definition():
    return RequirementDefinition(
        RequirementKind.USER,
        RequiredText("Retain intent"),
        "Full **Markdown**\n\nKeep hard breaks.  \n",
        (
            RequirementCriterion("C1", "Preserve identity"),
            RequirementCriterion("C2", "Preserve history"),
        ),
        "Local workspace",
    )


def requirement():
    return Requirement(
        EntityId(str(uuid4())), NOW, NOW, RequirementKey("UR-001"), definition()
    ).record("created", NOW, "Alice")


def test_rekey_and_metadata_preserve_uuid_and_intent():
    original = requirement()
    changed = original.rekey(RequirementKey("UR-012"), NOW, "Bob")
    changed = replace(changed, owner="Bob", priority=Priority.HIGH, rationale="Why")
    assert changed.id == original.id
    assert changed.current_revision == original.current_revision
    assert changed.revisions == original.revisions
    assert changed.history[:-1] == original.history
    assert changed.history[-1].actor == "Bob"
    assert changed.history[-1].reason == "UR-001 -> UR-012"


def test_line_endings_and_criterion_order_are_format_only():
    original = definition()
    changed = replace(
        original,
        statement=original.statement.replace("\n", "\r\n"),
        criteria=tuple(reversed(original.criteria)),
    )
    assert changed.fingerprint == original.fingerprint
    assert changed.statement != original.statement


@pytest.mark.parametrize(
    "changes",
    [
        {"statement": "Different outcome"},
        {"title": RequiredText("Different title")},
        {"scope": "Shared workspace"},
        {"criteria": (RequirementCriterion("C1", "Different coverage"),)},
        {"statement": "Full **Markdown**\n\nKeep hard breaks.\n"},
    ],
)
def test_intent_edits_preserve_prior_revision_and_history(changes):
    original = requirement()
    edited = replace(original, definition=replace(original.definition, **changes))
    assert edited.uncaptured_intent
    assert edited.current_revision != original.current_revision
    captured = edited.record("updated", NOW, "Bob")
    assert len(captured.revisions) == 2
    assert captured.revisions[0] == original.revisions[0]
    assert captured.history[:-1] == original.history
    assert not captured.uncaptured_intent


def test_manual_revision_return_reuses_definition_without_rewriting_reads():
    original = requirement()
    edited = replace(original, definition=replace(original.definition, statement="New"))
    captured = edited.record("updated", NOW, "Bob")
    returned = replace(captured, definition=original.definition)
    assert not returned.uncaptured_intent
    assert returned.record("updated", NOW, "Bob").revisions == captured.revisions


@pytest.mark.parametrize("key", ["UR-0", "UR-000", "UR-0001", "ur-001", "XY-001"])
def test_noncanonical_aliases_refuse(key):
    with pytest.raises(InvalidValue):
        RequirementKey(key)


def test_full_uuid_and_type_prefix_required():
    original = requirement()
    for changes in (
        {"id": EntityId("short-id")},
        {"id": EntityId("00000000-0000-1000-8000-000000000001")},
        {"key": RequirementKey("TR-001")},
    ):
        with pytest.raises(InvalidValue):
            replace(original, **changes)


def test_named_nonempty_unique_criteria_required():
    with pytest.raises(InvalidValue):
        replace(definition(), criteria=())
    with pytest.raises(InvalidValue):
        RequirementCriterion("../bad", "Text")
    with pytest.raises(InvalidValue):
        RequirementCriterion("C1", " ")
    with pytest.raises(InvalidValue):
        replace(definition(), criteria=(RequirementCriterion("C1", "A"),) * 2)
