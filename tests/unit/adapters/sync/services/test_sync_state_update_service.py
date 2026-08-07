"""Tests for SyncStateUpdateService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from roadmap.adapters.sync.services.sync_state_update_service import (
    SyncStateUpdateService,
)
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState


def test_update_baseline_for_pulled_updates_only_matching_ids():
    """Service should only update timestamps for pulled IDs present in baseline."""
    state_manager = MagicMock()
    baseline = SyncState(
        last_sync_time=datetime.now(UTC),
        base_issues={
            "1": IssueBaseState(id="1", status="todo"),
            "2": IssueBaseState(id="2", status="todo"),
        },
    )
    original_two = baseline.base_issues["2"].updated_at
    state_manager.load_sync_state_from_db.return_value = baseline

    service = SyncStateUpdateService(state_manager)
    service.update_baseline_for_pulled(["1", "missing"])

    state_manager.save_sync_state_to_db.assert_called_once_with(baseline)
    assert baseline.base_issues["1"].updated_at is not None
    assert baseline.base_issues["2"].updated_at == original_two


def test_update_baseline_for_pulled_no_baseline_no_save():
    """When no baseline exists, service should return without persistence."""
    state_manager = MagicMock()
    state_manager.load_sync_state_from_db.return_value = None

    service = SyncStateUpdateService(state_manager)
    service.update_baseline_for_pulled(["1"])

    state_manager.save_sync_state_to_db.assert_not_called()


def test_update_baseline_for_pulled_swallow_errors_and_log():
    """State update exceptions should be logged and not re-raised."""
    state_manager = MagicMock()
    state_manager.load_sync_state_from_db.side_effect = RuntimeError("db down")
    service = SyncStateUpdateService(state_manager)

    with patch(
        "roadmap.adapters.sync.services.sync_state_update_service.logger"
    ) as mock_logger:
        service.update_baseline_for_pulled(["1", "2"])

    mock_logger.error.assert_called_once()
    assert mock_logger.error.call_args.args[0] == "update_sync_state_failed"
