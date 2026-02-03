"""Tests for SyncMergeEngine (Tier 2 coverage)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from roadmap.adapters.sync.sync_merge_engine import SyncMergeEngine
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.sync_conflict_resolver import (
    ConflictStrategy,
    SyncConflictResolver,
)
from roadmap.core.services.sync.sync_plan import Action, PushAction
from roadmap.core.services.sync.sync_report import SyncReport
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from roadmap.core.services.sync.sync_state_manager import SyncStateManager


class TestSyncMergeEngine:
    """Test suite for SyncMergeEngine."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        core = MagicMock()
        core.roadmap_dir = "/tmp/roadmap"
        core.issues = MagicMock()
        core.db = MagicMock()
        return core

    @pytest.fixture
    def mock_backend(self):
        """Create mock SyncBackendInterface."""
        backend = MagicMock()
        backend.authenticate.return_value = True
        backend.get_issues.return_value = {}
        backend.push_issue.return_value = True
        return backend

    @pytest.fixture
    def mock_state_comparator(self):
        """Create mock SyncStateComparator."""
        return MagicMock(spec=SyncStateComparator)

    @pytest.fixture
    def mock_conflict_resolver(self):
        """Create mock SyncConflictResolver."""
        return MagicMock(spec=SyncConflictResolver)

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock SyncStateManager."""
        return MagicMock(spec=SyncStateManager)

    @pytest.fixture
    def engine(
        self,
        mock_core,
        mock_backend,
        mock_state_comparator,
        mock_conflict_resolver,
        mock_state_manager,
    ):
        """Create SyncMergeEngine instance."""
        with patch("roadmap.adapters.sync.sync_merge_engine.RemoteIssueCreationService"), \
             patch("roadmap.adapters.sync.sync_merge_engine.SyncStateUpdateService"), \
             patch("roadmap.adapters.sync.sync_merge_engine.BaselineStateHandler"), \
             patch("roadmap.adapters.sync.sync_merge_engine.ConflictConverter"):
            engine = SyncMergeEngine(
                core=mock_core,
                backend=mock_backend,
                state_comparator=mock_state_comparator,
                conflict_resolver=mock_conflict_resolver,
                state_manager=mock_state_manager,
            )
            # Replace with mocks for testing
            engine._baseline_handler = MagicMock()
            engine._conflict_converter = MagicMock()
            engine._issue_creation_service = MagicMock()
            engine._state_update_service = MagicMock()
        return engine

    def test_init_stores_parameters(
        self,
        mock_core,
        mock_backend,
        mock_state_comparator,
        mock_conflict_resolver,
        mock_state_manager,
    ):
        """Test initialization stores all parameters."""
        engine = SyncMergeEngine(
            core=mock_core,
            backend=mock_backend,
            state_comparator=mock_state_comparator,
            conflict_resolver=mock_conflict_resolver,
            state_manager=mock_state_manager,
        )

        assert engine.core is mock_core
        assert engine.backend is mock_backend
        assert engine.state_comparator is mock_state_comparator
        assert engine.conflict_resolver is mock_conflict_resolver
        assert engine.state_manager is mock_state_manager

    def test_init_creates_delegated_services(self, engine):
        """Test initialization creates delegated services."""
        assert engine._issue_creation_service is not None
        assert engine._state_update_service is not None
        assert engine._baseline_handler is not None
        assert engine._conflict_converter is not None

    def test_load_baseline_state(self, engine):
        """Test _load_baseline_state delegates to baseline handler."""
        expected_state = MagicMock()
        engine._baseline_handler.load_baseline_state.return_value = expected_state

        result = engine._load_baseline_state()

        assert result is expected_state
        engine._baseline_handler.load_baseline_state.assert_called_once()

    def test_process_fetched_pull_result(self, engine):
        """Test _process_fetched_pull_result delegates to processor."""
        fetched_result = {"remote_id": "123"}

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.PullResultProcessor"
        ) as mock_processor:
            mock_processor.process_pull_result.return_value = (1, [], ["123"])
            result = engine._process_fetched_pull_result(fetched_result)

        assert result == (1, [], ["123"])
        mock_processor.process_pull_result.assert_called_once_with(fetched_result)

    def test_update_baseline_for_pulled(self, engine):
        """Test _update_baseline_for_pulled delegates to baseline handler."""
        pulled_ids = ["123", "456"]

        engine._update_baseline_for_pulled(pulled_ids)

        engine._baseline_handler.update_baseline_for_pulled.assert_called_once_with(
            pulled_ids
        )

    def test_filter_unchanged_issues_from_base(self, engine):
        """Test _filter_unchanged_issues_from_base delegates to filter."""
        issues = [MagicMock(id="1"), MagicMock(id="2")]
        current_local = {"1": {}, "2": {}}
        base_state = {"1": {}, "2": {}}

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.LocalChangeFilter"
        ) as mock_filter:
            mock_filter.filter_unchanged_from_base.return_value = issues
            result = engine._filter_unchanged_issues_from_base(
                issues, current_local, base_state
            )

        assert result == issues
        mock_filter.filter_unchanged_from_base.assert_called_once()

    def test_convert_issue_changes_to_conflicts(self, engine):
        """Test _convert_issue_changes_to_conflicts delegates to converter."""
        changes = [MagicMock()]

        engine._conflict_converter.convert_changes_to_conflicts.return_value = []
        result = engine._convert_issue_changes_to_conflicts(changes)

        assert result == []
        engine._conflict_converter.convert_changes_to_conflicts.assert_called_once_with(
            changes
        )

    def test_create_issue_from_remote(self, engine):
        """Test _create_issue_from_remote delegates to service."""
        remote_issue = SyncIssue(
            id="123",
            title="Test Issue",
            status="open",
            headline="Test",
        )

        with patch.object(
            engine._issue_creation_service,
            "create_issue_from_remote",
            return_value=MagicMock(id="local-1"),
        ) as mock_create:
            result = engine._create_issue_from_remote("456", remote_issue)

        assert result.id == "local-1"
        mock_create.assert_called_once_with("456", remote_issue)

    def test_analyze_changes(self, engine):
        """Test _analyze_changes delegates to state comparator."""
        local_dict = {"1": MagicMock()}
        remote_data = {"1": {}}
        base_state = MagicMock()
        base_state.issues = {}

        engine.state_comparator.analyze_three_way.return_value = []
        result = engine._analyze_changes(local_dict, remote_data, base_state)

        assert result == []
        engine.state_comparator.analyze_three_way.assert_called_once()

    def test_analyze_and_classify_no_changes(self, engine):
        """Test _analyze_and_classify with no changes."""
        change = MagicMock()
        change.has_conflict = False
        change.is_local_only_change.return_value = False
        change.is_remote_only_change.return_value = False
        change.conflict_type = "no_change"
        change.local_state = None
        change.issue_id = "1"

        engine.state_comparator.analyze_three_way.return_value = [change]

        result = engine._analyze_and_classify({}, {}, None)

        assert len(result) == 8
        changes, conflicts, local_only, remote_only, no_changes, updates, pulls, up_to_date = result
        assert changes == [change]
        assert conflicts == []
        assert no_changes == [change]
        assert up_to_date == ["1"]

    def test_analyze_and_classify_with_conflicts(self, engine):
        """Test _analyze_and_classify with conflicts."""
        conflict_change = MagicMock()
        conflict_change.has_conflict = True
        conflict_change.is_local_only_change.return_value = False
        conflict_change.is_remote_only_change.return_value = False

        engine.state_comparator.analyze_three_way.return_value = [conflict_change]

        result = engine._analyze_and_classify({}, {}, None)

        _, conflicts, _, _, _, _, _, _ = result
        assert conflicts == [conflict_change]

    def test_analyze_and_classify_with_local_only_change(self, engine):
        """Test _analyze_and_classify with local-only changes."""
        local_change = MagicMock()
        local_change.has_conflict = False
        local_change.is_local_only_change.return_value = True
        local_change.is_remote_only_change.return_value = False
        local_change.conflict_type = "local_only"
        local_state = MagicMock()
        local_state.id = "1"
        local_change.local_state = local_state
        local_change.issue_id = "1"

        engine.state_comparator.analyze_three_way.return_value = [local_change]

        result = engine._analyze_and_classify({}, {}, None)

        _, _, local_only, _, _, updates, _, _ = result
        assert local_only == [local_change]
        assert updates == [local_state]

    def test_analyze_and_classify_with_remote_only_change(self, engine):
        """Test _analyze_and_classify with remote-only changes."""
        remote_change = MagicMock()
        remote_change.has_conflict = False
        remote_change.is_local_only_change.return_value = False
        remote_change.is_remote_only_change.return_value = True
        remote_change.conflict_type = "remote_only"
        remote_change.issue_id = "456"
        remote_change.local_state = None

        engine.state_comparator.analyze_three_way.return_value = [remote_change]

        result = engine._analyze_and_classify({}, {}, None)

        _, _, _, remote_only, _, _, pulls, _ = result
        assert remote_only == [remote_change]
        assert pulls == ["456"]

    def test_resolve_conflicts_no_conflicts(self, engine):
        """Test _resolve_conflicts_if_needed with no conflicts."""
        result = engine._resolve_conflicts_if_needed([], False, False)

        assert result == []
        engine.conflict_resolver.resolve_batch.assert_not_called()

    def test_resolve_conflicts_with_force_local(self, engine):
        """Test _resolve_conflicts_if_needed with force_local."""
        conflict = MagicMock()
        engine._conflict_converter.convert_changes_to_conflicts.return_value = [
            conflict
        ]
        engine.conflict_resolver.resolve_batch.return_value = [MagicMock(id="1")]

        result = engine._resolve_conflicts_if_needed([conflict], force_local=True, force_remote=False)

        assert len(result) == 1
        engine.conflict_resolver.resolve_batch.assert_called_once()
        call_args = engine.conflict_resolver.resolve_batch.call_args
        assert call_args[0][1] == ConflictStrategy.KEEP_LOCAL

    def test_resolve_conflicts_with_force_remote(self, engine):
        """Test _resolve_conflicts_if_needed with force_remote."""
        conflict = MagicMock()
        engine._conflict_converter.convert_changes_to_conflicts.return_value = [
            conflict
        ]
        engine.conflict_resolver.resolve_batch.return_value = []

        result = engine._resolve_conflicts_if_needed([conflict], force_local=False, force_remote=True)

        call_args = engine.conflict_resolver.resolve_batch.call_args
        assert call_args[0][1] == ConflictStrategy.KEEP_REMOTE

    def test_resolve_conflicts_with_auto_merge(self, engine):
        """Test _resolve_conflicts_if_needed with auto merge (default)."""
        conflict = MagicMock()
        engine._conflict_converter.convert_changes_to_conflicts.return_value = [
            conflict
        ]
        engine.conflict_resolver.resolve_batch.return_value = []

        result = engine._resolve_conflicts_if_needed([conflict], force_local=False, force_remote=False)

        call_args = engine.conflict_resolver.resolve_batch.call_args
        assert call_args[0][1] == ConflictStrategy.AUTO_MERGE

    def test_resolve_conflicts_resolution_failure(self, engine):
        """Test _resolve_conflicts_if_needed when resolution fails."""
        conflict = MagicMock()
        engine._conflict_converter.convert_changes_to_conflicts.return_value = [
            conflict
        ]
        engine.conflict_resolver.resolve_batch.side_effect = RuntimeError("Resolution error")

        with patch("roadmap.adapters.sync.sync_merge_engine.logger"):
            result = engine._resolve_conflicts_if_needed([conflict], False, False)

        assert result == []

    def test_apply_plan_single_push(self, engine):
        """Test _apply_plan with single issue push."""
        issue = MagicMock()
        issue.id = "1"
        report = SyncReport()

        with patch.object(engine.backend, "push_issue", return_value=True):
            with patch(
                "roadmap.adapters.sync.sync_merge_engine.SyncPlanExecutor"
            ) as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor_class.return_value = mock_executor
                mock_report = SyncReport()
                mock_report.issues_pushed = 1
                mock_executor.execute.return_value = mock_report

                result_report = engine._apply_plan(
                    updates=[issue],
                    resolved_issues=[],
                    pulls=[],
                    dry_run=False,
                    push_only=False,
                    pull_only=False,
                    report=report,
                )

        assert result_report.issues_pushed == 1
        mock_executor.execute.assert_called_once()

    def test_apply_plan_single_pull(self, engine):
        """Test _apply_plan with single issue pull."""
        report = SyncReport()

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.SyncPlanExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor
            mock_report = SyncReport()
            mock_report.issues_pulled = 1
            mock_executor.execute.return_value = mock_report

            result_report = engine._apply_plan(
                updates=[],
                resolved_issues=[],
                pulls=["remote-1"],
                dry_run=False,
                push_only=False,
                pull_only=False,
                report=report,
            )

        assert result_report.issues_pulled == 1

    def test_apply_plan_mixed_operations(self, engine):
        """Test _apply_plan with mixed push and pull."""
        issue = MagicMock()
        issue.id = "1"
        report = SyncReport()

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.SyncPlanExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor
            mock_report = SyncReport()
            mock_report.issues_pushed = 1
            mock_report.issues_pulled = 1
            mock_executor.execute.return_value = mock_report

            result_report = engine._apply_plan(
                updates=[issue],
                resolved_issues=[],
                pulls=["remote-1"],
                dry_run=False,
                push_only=False,
                pull_only=False,
                report=report,
            )

        assert result_report.issues_pushed == 1
        assert result_report.issues_pulled == 1

    def test_apply_plan_dry_run(self, engine):
        """Test _apply_plan with dry_run=True."""
        issue = MagicMock()
        issue.id = "1"
        report = SyncReport()

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.SyncPlanExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor
            mock_report = SyncReport()
            mock_executor.execute.return_value = mock_report

            engine._apply_plan(
                updates=[issue],
                resolved_issues=[],
                pulls=[],
                dry_run=True,
                push_only=False,
                pull_only=False,
                report=report,
            )

        # Verify execute was called with dry_run=True
        call_args = mock_executor.execute.call_args
        assert call_args[1]["dry_run"] is True

    def test_apply_plan_updates_report_fields(self, engine):
        """Test _apply_plan updates report with push/pull counts."""
        issue1 = MagicMock()
        issue1.id = "1"
        issue2 = MagicMock()
        issue2.id = "2"
        report = SyncReport()
        report.issues_needs_push = 2
        report.issues_needs_pull = 1

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.SyncPlanExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor
            mock_report = SyncReport()
            mock_report.issues_pushed = 2
            mock_report.issues_pulled = 1
            mock_executor.execute.return_value = mock_report

            result_report = engine._apply_plan(
                updates=[issue1, issue2],
                resolved_issues=[],
                pulls=["r1"],
                dry_run=False,
                push_only=False,
                pull_only=False,
                report=report,
            )

        assert result_report.issues_pushed == 2
        assert result_report.issues_pulled == 1

    def test_apply_plan_handles_executor_error(self, engine):
        """Test _apply_plan handles executor error."""
        issue = MagicMock()
        issue.id = "1"
        report = SyncReport()

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.SyncPlanExecutor"
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor
            mock_report = SyncReport()
            mock_report.error = "Execution failed"
            mock_executor.execute.return_value = mock_report

            result_report = engine._apply_plan(
                updates=[issue],
                resolved_issues=[],
                pulls=[],
                dry_run=False,
                push_only=False,
                pull_only=False,
                report=report,
            )

        assert result_report.error == "Execution failed"

    def test_push_updates_single_issue_success(self, engine):
        """Test _push_updates with single issue push."""
        issue = MagicMock()
        issue.id = "1"
        issue.title = "Test"
        report = SyncReport()

        engine.backend.push_issue.return_value = True
        engine.state_manager.save_base_state.return_value = None

        pushed_count, errors = engine._push_updates([issue], report)

        assert pushed_count == 1
        assert errors == []
        engine.backend.push_issue.assert_called_once_with(issue)

    def test_push_updates_batch_issues_success(self, engine):
        """Test _push_updates with batch of issues."""
        issue1 = MagicMock()
        issue1.id = "1"
        issue2 = MagicMock()
        issue2.id = "2"
        report = SyncReport()

        push_report = MagicMock()
        push_report.errors = None
        engine.backend.push_issues.return_value = push_report
        engine.state_manager.save_base_state.return_value = None

        pushed_count, errors = engine._push_updates([issue1, issue2], report)

        assert pushed_count == 2
        assert errors == []

    def test_push_updates_with_errors(self, engine):
        """Test _push_updates when batch push fails."""
        issue1 = MagicMock()
        issue1.id = "1"
        issue2 = MagicMock()
        issue2.id = "2"
        report = SyncReport()

        push_report = MagicMock()
        push_report.errors = {"1": "Push failed"}
        engine.backend.push_issues.return_value = push_report

        with patch("roadmap.adapters.sync.sync_merge_engine.logger"):
            pushed_count, errors = engine._push_updates(
                [issue1, issue2], report
            )

        assert pushed_count == 0
        assert "1" in errors

    def test_pull_updates_success(self, engine):
        """Test _pull_updates successful pull."""
        report = SyncReport()

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.RemoteFetcher"
        ) as mock_fetcher:
            mock_fetcher.fetch_issues.return_value = {"123": {}}
            engine._process_fetched_pull_result = MagicMock(
                return_value=(1, [], ["123"])
            )

            pulled_count, errors = engine._pull_updates(["remote-1"])

        assert pulled_count == 1
        assert errors == []

    def test_pull_updates_error(self, engine):
        """Test _pull_updates with fetch error."""
        report = SyncReport()

        with patch(
            "roadmap.adapters.sync.sync_merge_engine.RemoteFetcher"
        ) as mock_fetcher:
            mock_fetcher.fetch_issues.side_effect = RuntimeError("Fetch failed")

            with patch("roadmap.adapters.sync.sync_merge_engine.logger"):
                pulled_count, errors = engine._pull_updates(["remote-1"])

        assert pulled_count == 0

    def test_match_and_link_no_remote_issues(self, engine):
        """Test _match_and_link_remote_issues with no remote issues."""
        result = engine._match_and_link_remote_issues({}, {})

        assert result == {
            "auto_linked": [],
            "potential_duplicates": [],
            "new_remote": [],
        }

    def test_match_and_link_already_linked(self, engine):
        """Test _match_and_link_remote_issues with already linked issue."""
        remote_data = {"123": MagicMock(title="Issue")}
        engine.core.db.remote_links.get_issue_uuid.return_value = "uuid-1"

        result = engine._match_and_link_remote_issues({}, remote_data)

        assert result["auto_linked"] == []
        assert result["new_remote"] == []


class TestSyncMergeEngineIntegration:
    """Integration tests for SyncMergeEngine."""

    def test_push_pull_round_trip(self):
        """Test push and pull operations in sequence."""
        mock_core = MagicMock()
        mock_backend = MagicMock()
        mock_comparator = MagicMock(spec=SyncStateComparator)
        mock_resolver = MagicMock(spec=SyncConflictResolver)
        mock_state_manager = MagicMock(spec=SyncStateManager)

        engine = SyncMergeEngine(
            core=mock_core,
            backend=mock_backend,
            state_comparator=mock_comparator,
            conflict_resolver=mock_resolver,
            state_manager=mock_state_manager,
        )

        # Setup for push
        issue_to_push = MagicMock()
        issue_to_push.id = "1"
        mock_backend.push_issue.return_value = True

        pushed, push_errors = engine._push_updates([issue_to_push], SyncReport())
        assert pushed == 1
        assert push_errors == []

        # Setup for pull
        with patch(
            "roadmap.adapters.sync.sync_merge_engine.RemoteFetcher"
        ) as mock_fetcher:
            mock_fetcher.fetch_issues.return_value = {"remote-1": {}}
            engine._process_fetched_pull_result = MagicMock(
                return_value=(1, [], ["remote-1"])
            )
            pulled, pull_errors = engine._pull_updates(["remote-1"])

        assert pulled == 1
        assert pull_errors == []
