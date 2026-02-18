"""Wave 2 tests for remote state normalization."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from roadmap.core.services.utils.remote_state_normalizer import RemoteStateNormalizer


def test_normalize_remote_state_returns_copy_for_dict() -> None:
    payload = {"id": "1", "status": "open"}

    result = RemoteStateNormalizer.normalize_remote_state(payload)

    assert result == payload
    assert result is not payload


def test_normalize_remote_state_extracts_known_fields_from_object() -> None:
    obj = SimpleNamespace(
        id="x-1",
        status="open",
        title="Title",
        content="Body",
        labels=["bug"],
        assignee="owner",
        milestone="M1",
        updated_at="2026-01-01T00:00:00Z",
    )

    result = RemoteStateNormalizer.normalize_remote_state(obj)

    assert result is not None
    assert result["id"] == "x-1"
    assert result["labels"] == ["bug"]
    assert result["updated_at"] == "2026-01-01T00:00:00Z"


def test_normalize_remote_state_returns_none_for_none() -> None:
    assert RemoteStateNormalizer.normalize_remote_state(None) is None


def test_extract_timestamp_handles_datetime_and_iso_strings() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    from_dict = RemoteStateNormalizer.extract_timestamp({"updated_at": now})
    from_obj = RemoteStateNormalizer.extract_timestamp(
        SimpleNamespace(updated_at="2026-01-02T10:30:00Z")
    )

    assert from_dict == now
    assert from_obj is not None
    assert from_obj.year == 2026
    assert from_obj.month == 1
    assert from_obj.day == 2


def test_extract_timestamp_returns_none_for_invalid_inputs() -> None:
    assert RemoteStateNormalizer.extract_timestamp({"updated_at": "nope"}) is None
    assert (
        RemoteStateNormalizer.extract_timestamp(
            SimpleNamespace(updated_at=None),
            field_name="updated_at",
        )
        is None
    )
