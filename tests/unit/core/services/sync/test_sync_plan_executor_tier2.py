"""Tests for SyncPlanExecutor (Tier 2 coverage)."""

from unittest.mock import MagicMock, patch

import pytest

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
        batch_result = MagicMock()
        batch_result.pushed = True
        executor.transport_adapter.push_issues.return_value = batch_result

        action = MagicMock()
        action.payload = {"issues": [{"id": 1}, {"id": 2}]}

        result = executor._handle_push(action, dry_run=False)

        executor.transport_adapter.push_issues.assert_called_once()
        assert result is True

    def test_handle_push_batch_fallback_to_single(self, executor):
        """Test _handle_push falls back to single push on batch failure."""
        executor.transport_adapter.push_issues.side_effect = Exception("Batch failed")
        executor.transport_adapter.push_issue.return_value = False

        action = MagicMock()
        action.payload = {"issues": [{"id": 1}], "issue": {"id": 1}}

        with patch("roadmap.core.services.sync.sync_plan_executor.logger"):
            result = executor._handle_push(action, dry_run=False)

        assert result is False

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
