"""Tests for SyncPlanExecutor (Tier 2 coverage)."""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.result import Err, Ok
from roadmap.core.services.sync.sync_errors import SyncError, SyncErrorType
from roadmap.core.services.sync.sync_plan_executor import SyncPlanExecutor
from roadmap.core.services.sync.sync_report import SyncReport


class TestSyncPlanExecutor:
    """Test suite for SyncPlanExecutor."""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock transport adapter."""
        return MagicMock()

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        return MagicMock()

    @pytest.fixture
    def executor(self, mock_adapter, mock_db_session, mock_core):
        """Create executor instance."""
        return SyncPlanExecutor(
            transport_adapter=mock_adapter,
            db_session=mock_db_session,
            core=mock_core,
        )

    def test_init_stores_parameters(self, mock_adapter, mock_db_session, mock_core):
        """Test that initialization stores all parameters."""
        executor = SyncPlanExecutor(
            transport_adapter=mock_adapter,
            db_session=mock_db_session,
            core=mock_core,
            stop_on_error=False,
        )

        assert executor.transport_adapter is mock_adapter
        assert executor.db_session is mock_db_session
        assert executor.core is mock_core
        assert executor.stop_on_error is False

    def test_init_defaults(self):
        """Test that initialization has correct defaults."""
        executor = SyncPlanExecutor()

        assert executor.transport_adapter is None
        assert executor.db_session is None
        assert executor.core is None
        assert executor.tracer is None
        assert executor.stop_on_error is True
        assert executor._created_local_ids == {}

    def test_execute_empty_plan(self, executor):
        """Test executing empty plan."""
        plan = MagicMock()
        plan.actions = []

        report = executor.execute(plan)

        assert isinstance(report, SyncReport)

    def test_execute_plan_with_actions(self, executor):
        """Test executing plan with actions."""
        action1 = MagicMock()
        action1.action_type = "push"
        action2 = MagicMock()
        action2.action_type = "pull"

        plan = MagicMock()
        plan.actions = [action1, action2]

        with patch.object(executor, "_apply_action", return_value=True):
            report = executor.execute(plan, dry_run=True)

        assert isinstance(report, SyncReport)

    def test_execute_dry_run_true(self, executor):
        """Test execute with dry_run=True."""
        action = MagicMock()
        action.action_type = "push"

        plan = MagicMock()
        plan.actions = [action]

        with patch.object(executor, "_apply_action", return_value=False) as mock_apply:
            executor.execute(plan, dry_run=True)
            mock_apply.assert_called_once_with(action, dry_run=True)

    def test_execute_dry_run_false(self, executor):
        """Test execute with dry_run=False."""
        action = MagicMock()
        action.action_type = "push"

        plan = MagicMock()
        plan.actions = [action]

        with patch.object(executor, "_apply_action", return_value=True) as mock_apply:
            report = executor.execute(plan, dry_run=False)
            mock_apply.assert_called_once_with(action, dry_run=False)
            assert report.issues_pushed == 1

    def test_execute_with_initial_report(self, executor):
        """Test execute with initial report."""
        initial_report = SyncReport()
        initial_report.issues_pulled = 5

        plan = MagicMock()
        plan.actions = []

        report = executor.execute(plan, initial_report=initial_report)

        assert report is initial_report
        assert report.issues_pulled == 5

    def test_execute_counts_pushed(self, executor):
        """Test that pushed issues are counted."""
        action = MagicMock()
        action.action_type = "push"

        plan = MagicMock()
        plan.actions = [action]

        with patch.object(executor, "_apply_action", return_value=True):
            report = executor.execute(plan, dry_run=False)

        assert report.issues_pushed == 1

    def test_execute_counts_pulled(self, executor):
        """Test that pulled issues are counted."""
        action = MagicMock()
        action.action_type = "pull"

        plan = MagicMock()
        plan.actions = [action]

        with patch.object(executor, "_apply_action", return_value=True):
            report = executor.execute(plan, dry_run=False)

        assert report.issues_pulled == 1

    def test_execute_mixed_actions(self, executor):
        """Test executing mixed action types."""
        actions = [
            MagicMock(action_type="push"),
            MagicMock(action_type="pull"),
            MagicMock(action_type="push"),
        ]

        plan = MagicMock()
        plan.actions = actions

        with patch.object(executor, "_apply_action", return_value=True):
            report = executor.execute(plan, dry_run=False)

        assert report.issues_pushed == 2
        assert report.issues_pulled == 1

    def test_execute_stops_on_error(self, executor):
        """Test execution stops on error when stop_on_error=True."""
        executor.stop_on_error = True

        action1 = MagicMock()
        action2 = MagicMock()

        plan = MagicMock()
        plan.actions = [action1, action2]

        def side_effect(action, dry_run):
            raise ValueError("Test error")

        with patch.object(executor, "_apply_action", side_effect=side_effect):
            with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
                report = executor.execute(plan, dry_run=False)

        assert report.error == "Test error"

    def test_execute_continues_on_error(self, executor):
        """Test execution continues on error when stop_on_error=False."""
        executor.stop_on_error = False

        actions = [
            MagicMock(action_type="push"),
            MagicMock(action_type="pull"),
        ]

        plan = MagicMock()
        plan.actions = actions

        call_count = 0

        def side_effect(action, dry_run):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First error")
            return True

        with patch.object(executor, "_apply_action", side_effect=side_effect):
            with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
                executor.execute(plan, dry_run=False)

        assert call_count == 2

    @patch("roadmap.core.services.sync.sync_plan_executor.logger")
    def test_execute_logs_error(self, mock_logger, executor):
        """Test that errors are logged."""
        action = MagicMock()
        action.action_type = "push"

        plan = MagicMock()
        plan.actions = [action]

        def side_effect(action, dry_run):
            raise RuntimeError("Test error")

        with patch.object(executor, "_apply_action", side_effect=side_effect):
            executor.execute(plan, dry_run=False)

        assert mock_logger.error.called

    def test_apply_action_push(self, executor):
        """Test _apply_action routes to _handle_push."""
        action = MagicMock(action_type="push")

        with patch.object(executor, "_handle_push", return_value=True) as mock_handle:
            result = executor._apply_action(action, dry_run=True)

        mock_handle.assert_called_once_with(action, dry_run=True)
        assert result is True

    def test_apply_action_pull(self, executor):
        """Test _apply_action routes to _handle_pull."""
        action = MagicMock(action_type="pull")

        with patch.object(executor, "_handle_pull", return_value=True) as mock_handle:
            executor._apply_action(action, dry_run=True)

        mock_handle.assert_called_once_with(action, dry_run=True)

    def test_apply_action_create_local(self, executor):
        """Test _apply_action routes to _handle_create_local."""
        action = MagicMock(action_type="create_local")

        with patch.object(
            executor, "_handle_create_local", return_value=True
        ) as mock_handle:
            executor._apply_action(action, dry_run=True)

        mock_handle.assert_called_once_with(action, dry_run=True)

    def test_apply_action_link(self, executor):
        """Test _apply_action routes to _handle_link."""
        action = MagicMock(action_type="link")

        with patch.object(executor, "_handle_link", return_value=True) as mock_handle:
            executor._apply_action(action, dry_run=True)

        mock_handle.assert_called_once_with(action, dry_run=True)

    def test_apply_action_update_baseline(self, executor):
        """Test _apply_action routes to _handle_update_baseline."""
        action = MagicMock(action_type="update_baseline")

        with patch.object(
            executor, "_handle_update_baseline", return_value=True
        ) as mock_handle:
            executor._apply_action(action, dry_run=True)

        mock_handle.assert_called_once_with(action, dry_run=True)

    def test_apply_action_resolve_conflict(self, executor):
        """Test _apply_action routes to _handle_resolve_conflict."""
        action = MagicMock(action_type="resolve_conflict")

        with patch.object(
            executor, "_handle_resolve_conflict", return_value=True
        ) as mock_handle:
            executor._apply_action(action, dry_run=True)

        mock_handle.assert_called_once_with(action, dry_run=True)

    def test_apply_action_unknown(self, executor):
        """Test _apply_action returns None for unknown action."""
        action = MagicMock(action_type="unknown")

        result = executor._apply_action(action, dry_run=True)

        assert result is None

    def test_handle_push_returns_false_on_dry_run(self, executor):
        """Test _handle_push returns False during dry_run."""
        action = MagicMock()
        action.payload = {"issue": {"id": 1}}

        result = executor._handle_push(action, dry_run=True)

        assert result is False

    def test_handle_push_returns_false_no_adapter(self, executor):
        """Test _handle_push returns False when no adapter."""
        executor.transport_adapter = None
        action = MagicMock()
        action.payload = {"issue": {"id": 1}}

        result = executor._handle_push(action, dry_run=False)

        assert result is False

    def test_handle_push_single_issue(self, executor):
        """Test _handle_push with single issue."""
        executor.transport_adapter.push_issue.return_value = True

        action = MagicMock()
        action.payload = {"issue": {"id": 1}}

        result = executor._handle_push(action, dry_run=False)

        executor.transport_adapter.push_issue.assert_called_once_with({"id": 1})
        assert result is True

    def test_handle_push_batch_issues(self, executor):
        """Test _handle_push with batch issues."""
        batch_report = MagicMock()
        batch_report.pushed = [{"id": 1}, {"id": 2}]  # Return list of pushed items
        executor.transport_adapter.push_issues.return_value = Ok(batch_report)

        action = MagicMock()
        action.payload = {"issues": [{"id": 1}, {"id": 2}]}

        result = executor._handle_push(action, dry_run=False)

        executor.transport_adapter.push_issues.assert_called_once()
        assert result == 2

    def test_handle_push_batch_fallback_to_single(self, executor):
        """Test _handle_push falls back to single push on batch failure."""
        executor.transport_adapter.push_issues.side_effect = Exception("Batch failed")
        executor.transport_adapter.push_issue.return_value = False

        action = MagicMock()
        action.payload = {"issues": [{"id": 1}], "issue": {"id": 1}}

        with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
            result = executor._handle_push(action, dry_run=False)

        assert result is False

    def test_handle_push_batch_result_ok(self, executor):
        """Test _handle_push unwraps Result.Ok for batch push."""
        report = MagicMock()
        report.pushed = ["1", "2", "3"]
        executor.transport_adapter.push_issues.return_value = Ok(report)

        action = MagicMock()
        action.payload = {"issues": [{"id": 1}, {"id": 2}, {"id": 3}]}

        result = executor._handle_push(action, dry_run=False)

        assert result == 3

    def test_handle_push_batch_result_err_records_error(self, executor):
        """Test _handle_push records Err when stop_on_error is False."""
        executor.stop_on_error = False
        error = SyncError(
            error_type=SyncErrorType.NETWORK_ERROR,
            message="Network down",
            entity_type="Issue",
            entity_id="123",
        )
        executor.transport_adapter.push_issues.return_value = Err(error)

        action = MagicMock()
        action.payload = {"issues": [{"id": 123}]}

        result = executor._handle_push(action, dry_run=False)

        assert result is False
        assert executor._accumulated_errors.get("123") == str(error)

    def test_handle_pull_batch_issues(self, executor):
        """Test _handle_pull with batch issues."""
        batch_report = MagicMock()
        batch_report.pulled = [{"id": 1}, {"id": 2}]
        executor.transport_adapter.pull_issues.return_value = Ok(batch_report)

        action = MagicMock()
        action.payload = {"issue_ids": ["1", "2"]}

        result = executor._handle_pull(action, dry_run=False)

        executor.transport_adapter.pull_issues.assert_called_once()
        assert result == 2

    def test_handle_pull_batch_result_ok(self, executor):
        """Test _handle_pull unwraps Result.Ok for batch pull."""
        report = MagicMock()
        report.pulled = ["1", "2"]
        executor.transport_adapter.pull_issues.return_value = Ok(report)

        action = MagicMock()
        action.payload = {"issue_ids": ["1", "2"]}

        result = executor._handle_pull(action, dry_run=False)

        assert result == 2

    def test_handle_pull_batch_result_err_records_error(self, executor):
        """Test _handle_pull records Err when stop_on_error is False."""
        executor.stop_on_error = False
        error = SyncError(
            error_type=SyncErrorType.API_RATE_LIMIT,
            message="Rate limited",
            entity_type="Issue",
            entity_id="456",
        )
        executor.transport_adapter.pull_issues.return_value = Err(error)

        action = MagicMock()
        action.payload = {"issue_ids": ["456"]}

        result = executor._handle_pull(action, dry_run=False)

        assert result is False
        assert executor._accumulated_errors.get("456") == str(error)

    def test_created_local_ids_cache(self, executor):
        """Test _created_local_ids cache is initialized."""
        assert executor._created_local_ids == {}

    def test_created_local_ids_persists(self, executor):
        """Test _created_local_ids can be manipulated."""
        executor._created_local_ids["key"] = "value"

        assert executor._created_local_ids["key"] == "value"


class TestSyncPlanExecutorIntegration:
    """Integration tests for SyncPlanExecutor."""

    def test_full_sync_execution(self):
        """Test full sync execution flow."""
        executor = SyncPlanExecutor(
            transport_adapter=MagicMock(),
            db_session=MagicMock(),
            stop_on_error=True,
        )

        plan = MagicMock()
        plan.actions = [
            MagicMock(action_type="push"),
            MagicMock(action_type="pull"),
        ]

        with patch.object(executor, "_apply_action", return_value=True):
            report = executor.execute(plan, dry_run=False)

        assert report.issues_pushed == 1
        assert report.issues_pulled == 1

    def test_error_handling_with_report(self):
        """Test error is recorded in report."""
        executor = SyncPlanExecutor(stop_on_error=True)

        plan = MagicMock()
        plan.actions = [MagicMock(action_type="push")]

        with patch.object(
            executor, "_apply_action", side_effect=RuntimeError("Test failure")
        ):
            with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
                report = executor.execute(plan, dry_run=False)

        assert report.error and "Test failure" in report.error


class TestSyncPlanExecutorBehavior:
    """Additional behavior coverage for core executor handlers."""

    @pytest.fixture
    def executor(self):
        return SyncPlanExecutor(
            transport_adapter=MagicMock(),
            db_session=MagicMock(),
            core=MagicMock(),
            stop_on_error=False,
        )

    def test_unwrap_result_ok_passthrough(self, executor):
        value = {"ok": True}
        assert executor._unwrap_result(Ok(value), operation="push_issue") == value

    def test_unwrap_result_err_records_and_returns_none_when_not_stopping(
        self, executor
    ):
        err = SyncError(
            error_type=SyncErrorType.VALIDATION_ERROR,
            message="invalid",
            entity_type="Issue",
            entity_id="I-1",
        )
        result = executor._unwrap_result(Err(err), operation="push_issue")
        assert result is None
        assert executor._accumulated_errors["I-1"] == str(err)

    def test_unwrap_result_err_raises_when_stop_on_error_true(self):
        executor = SyncPlanExecutor(stop_on_error=True)
        err = SyncError(
            error_type=SyncErrorType.NETWORK_ERROR,
            message="boom",
            entity_type="Issue",
            entity_id="I-2",
        )

        with pytest.raises(RuntimeError, match="boom"):
            executor._unwrap_result(Err(err), operation="pull_issue")

    def test_record_result_error_uses_operation_and_deconflicts_keys(self, executor):
        executor._record_result_error("push_issue", "first")
        executor._record_result_error("push_issue", "second")
        assert "push_issue" in executor._accumulated_errors
        assert any(
            key.startswith("push_issue:") for key in executor._accumulated_errors
        )

    def test_handle_create_local_dry_run_caches_fake_id(self, executor):
        action = MagicMock(payload={"remote_id": "42", "remote": {"title": "R"}})
        created = executor._handle_create_local(action, dry_run=True)
        assert created == "dry-42"
        assert executor._created_local_ids["42"] == "dry-42"

    def test_handle_create_local_prefers_core_issue_service(self, executor):
        issue_obj = MagicMock(id="L-100")
        executor.core.issue_service.create_issue.return_value = issue_obj
        action = MagicMock(payload={"remote_id": "99", "remote": {"title": "X"}})

        created = executor._handle_create_local(action, dry_run=False)

        assert created == "L-100"
        executor.core.issue_service.create_issue.assert_called_once()
        assert executor._created_local_ids["99"] == "L-100"

    def test_handle_create_local_core_exception_returns_none(self, executor):
        executor.core.issue_service.create_issue.side_effect = RuntimeError("core fail")
        action = MagicMock(payload={"remote_id": "77", "remote": {"title": "Y"}})

        with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
            created = executor._handle_create_local(action, dry_run=False)

        assert created is None

    def test_handle_create_local_uses_db_session_when_core_service_missing(
        self, executor
    ):
        executor.core.issue_service = None
        executor.db_session.create_issue.return_value = "L-200"
        action = MagicMock(payload={"remote_id": "77", "remote": {"title": "Y"}})

        created = executor._handle_create_local(action, dry_run=False)

        assert created == "L-200"
        assert executor._created_local_ids["77"] == "L-200"

    def test_handle_link_uses_core_repo_when_available(self, executor):
        action = MagicMock(
            payload={"issue_id": "L-1", "backend": "github", "remote_id": "10"}
        )
        with patch(
            "roadmap.infrastructure.sync_gateway.SyncGateway.link_issue_in_database",
            return_value=True,
        ) as mock_link:
            assert executor._handle_link(action, dry_run=False) is True
            mock_link.assert_called_once_with(
                executor.core.remote_link_repo, "L-1", "github", "10"
            )

    def test_handle_update_baseline_core_then_db_fallback(self, executor):
        action = MagicMock(payload={"baseline": {"A": {"status": "todo"}}})

        assert executor._handle_update_baseline(action, dry_run=True) is True

        executor.core.db.set_sync_baseline.side_effect = RuntimeError("core db fail")
        with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
            assert executor._handle_update_baseline(action, dry_run=False) is False

    def test_handle_update_baseline_uses_db_session_when_core_missing_method(
        self, executor
    ):
        action = MagicMock(payload={"baseline": {"A": {"status": "todo"}}})
        executor.core.db = MagicMock(spec=[])
        executor.db_session.set_sync_baseline.return_value = True

        assert executor._handle_update_baseline(action, dry_run=False) is True

    def test_handle_resolve_conflict_adapter_and_core_fallback(self, executor):
        action = MagicMock(
            payload={"issue_id": "L-3", "resolution": {"status": "closed"}}
        )

        assert executor._handle_resolve_conflict(action, dry_run=True) is True

        executor.transport_adapter.resolve_conflict.side_effect = RuntimeError(
            "adapter fail"
        )
        executor.core.db.apply_conflict_resolution.return_value = True

        with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
            assert executor._handle_resolve_conflict(action, dry_run=False) is False

        # Remove adapter method path and validate core DB fallback path
        executor.transport_adapter = MagicMock(spec=[])
        assert executor._handle_resolve_conflict(action, dry_run=False) is True
