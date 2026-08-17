"""Pure contracts for the target Application boundary."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from roadmap.application.contracts import GitSnapshot, IssueDraft, MutationReceipt
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.domain.types import EntityId, Timestamp, Title


def test_request_and_response_contracts_are_immutable() -> None:
    draft = IssueDraft(Title("Capture work"))
    receipt = MutationReceipt(
        EntityId("issue-id"), Timestamp(datetime(2026, 8, 16, tzinfo=UTC))
    )

    with pytest.raises(FrozenInstanceError):
        draft.headline = "changed"  # type: ignore[misc]
    assert receipt.entity_id == "issue-id"


def test_local_git_response_contains_data_without_running_git() -> None:
    snapshot = GitSnapshot("main", "abc123", (".roadmap/issues/issue-id.md",))

    assert snapshot.changed_paths == (".roadmap/issues/issue-id.md",)


def test_application_failures_have_stable_categories() -> None:
    failure = ApplicationFailure(FailureCategory.NOT_FOUND, "issue was not found")

    assert failure.category is FailureCategory.NOT_FOUND
    assert str(failure) == "issue was not found"
