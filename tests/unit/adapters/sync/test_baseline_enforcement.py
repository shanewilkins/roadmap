"""Tests for SyncRetrievalOrchestrator baseline enforcement.

Tests the baseline enforcement mechanisms that ensure explicit baseline
creation during first sync.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.sync.sync_retrieval_orchestrator import (
    SyncRetrievalOrchestrator,
)
from roadmap.core.models.sync_state import IssueBaseState, SyncState
from roadmap.core.services.baseline_selector import BaselineStrategy


class TestBaselineEnforcement:
    """Test baseline enforcement in SyncRetrievalOrchestrator."""

    @pytest.fixture
    def mock_core(self):
        """Create mock RoadmapCore."""
        mock = MagicMock()
        mock.roadmap_dir = Path("/test/roadmap")
        mock.issues_dir = Path("/test/roadmap/issues")
        mock.issues = MagicMock()
        mock.issues.list = MagicMock(return_value=[])
        # Mock database to return no baseline by default
        mock.db = MagicMock()
        mock.db.get_sync_baseline = MagicMock(return_value=None)
        return mock

    @pytest.fixture
    def mock_backend(self):
        """Create mock backend."""
        mock = MagicMock()
        mock.authenticate = MagicMock(return_value=True)
        mock.get_issues = MagicMock(return_value={})
        mock.__class__.__name__ = "MockBackend"
        return mock

    @pytest.fixture
    def orchestrator(self, mock_core, mock_backend):
        """Create orchestrator with mocks."""
        with patch(
            "roadmap.adapters.sync.sync_retrieval_orchestrator.BaselineStateRetriever"
        ):
            orchestrator = SyncRetrievalOrchestrator(
                core=mock_core,
                backend=mock_backend,
            )
            # Mock state_manager
            orchestrator.state_manager = MagicMock()
            return orchestrator

    def test_has_baseline_returns_false_when_no_state(self, orchestrator):
        """Test has_baseline returns False when no sync state exists."""
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=None)
        assert orchestrator.has_baseline() is False

    def test_has_baseline_returns_false_when_empty_state(self, orchestrator):
        """Test has_baseline returns False when sync state has no issues."""
        empty_state = SyncState(
            last_sync=datetime.now(timezone.utc),
            backend="test",
        )
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=empty_state)
        assert orchestrator.has_baseline() is False

    def test_has_baseline_returns_true_when_state_exists(self, orchestrator):
        """Test has_baseline returns True when sync state has issues."""
        baseline_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Test",
        )
        state = SyncState(
            last_sync=datetime.now(timezone.utc),
            backend="test",
        )
        state.issues["issue-1"] = baseline_state
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=state)
        assert orchestrator.has_baseline() is True

    def test_ensure_baseline_returns_true_when_baseline_exists(self, orchestrator):
        """Test ensure_baseline returns True when baseline already exists."""
        baseline_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Test",
        )
        state = SyncState(
            last_sync=datetime.now(timezone.utc),
            backend="test",
        )
        state.issues["issue-1"] = baseline_state
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=state)

        result = orchestrator.ensure_baseline(interactive=False)
        assert result is True

    def test_ensure_baseline_raises_when_no_baseline_and_not_interactive(
        self, orchestrator
    ):
        """Test ensure_baseline raises when baseline missing and interactive=False."""
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=None)

        with pytest.raises(RuntimeError, match="Baseline required"):
            orchestrator.ensure_baseline(interactive=False)

    def test_ensure_baseline_creates_from_local(self, orchestrator):
        """Test ensure_baseline creates baseline from local when strategy=LOCAL."""
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=None)

        with patch.object(
            orchestrator, "_create_baseline_from_local", return_value=True
        ):
            result = orchestrator.ensure_baseline(
                strategy=BaselineStrategy.LOCAL, interactive=False
            )
        assert result is True

    def test_ensure_baseline_creates_from_remote(self, orchestrator):
        """Test ensure_baseline creates baseline from remote when strategy=REMOTE."""
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=None)

        with patch.object(
            orchestrator, "_create_baseline_from_remote", return_value=True
        ):
            result = orchestrator.ensure_baseline(
                strategy=BaselineStrategy.REMOTE, interactive=False
            )
        assert result is True

    def test_create_baseline_from_local_succeeds(self, orchestrator):
        """Test creating baseline from local issues."""
        baseline_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Test Issue",
        )
        mock_sync_state = SyncState(
            last_sync=datetime.now(timezone.utc),
            backend="test",
        )
        mock_sync_state.issues["issue-1"] = baseline_state

        with patch.object(
            orchestrator, "_create_initial_baseline", return_value=mock_sync_state
        ):
            result = orchestrator._create_baseline_from_local()

        assert result is True
        # Mock the database save method instead of state_manager
        orchestrator.core.db.save_sync_baseline.assert_called_once()

    def test_create_baseline_from_local_fails_when_empty(self, orchestrator):
        """Test creating baseline from local fails with empty state."""
        empty_state = SyncState(
            last_sync=datetime.now(timezone.utc),
            backend="test",
        )

        with patch.object(
            orchestrator, "_create_initial_baseline", return_value=empty_state
        ):
            result = orchestrator._create_baseline_from_local()

        assert result is False

    def test_create_baseline_from_remote_succeeds(self, orchestrator):
        """Test creating baseline from remote issues."""
        from datetime import datetime

        from roadmap.core.models.sync_models import SyncIssue

        remote_issues = {
            "issue-1": SyncIssue(
                id="issue-1",
                title="Remote Issue",
                status="todo",
                assignee="alice",
                labels=["bug"],
                description="Test",
                backend_name="mock",
                backend_id="1",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        }

        orchestrator.backend.get_issues.return_value = remote_issues

        result = orchestrator._create_baseline_from_remote()

        assert result is True
        # Mock the database save method instead of state_manager
        orchestrator.core.db.save_sync_baseline.assert_called_once()

        # Check that the saved baseline has the remote issue data
        saved_baseline = orchestrator.core.db.save_sync_baseline.call_args[0][0]
        assert "issue-1" in saved_baseline

    def test_create_baseline_from_remote_fails_when_auth_fails(self, orchestrator):
        """Test creating baseline from remote fails when auth fails."""
        orchestrator.backend.authenticate.return_value = False

        result = orchestrator._create_baseline_from_remote()

        assert result is False

    def test_create_baseline_from_remote_fails_when_no_issues(self, orchestrator):
        """Test creating baseline from remote fails when no issues returned."""
        orchestrator.backend.get_issues.return_value = None

        result = orchestrator._create_baseline_from_remote()

        assert result is False

    def test_ensure_baseline_with_interactive_prompt(self, orchestrator):
        """Test ensure_baseline with interactive prompt."""
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=None)

        # Mock the baseline selector
        mock_result = MagicMock()
        mock_result.strategy = BaselineStrategy.LOCAL
        orchestrator.baseline_selector.select_baseline = MagicMock(
            return_value=mock_result
        )

        with patch.object(
            orchestrator, "_create_baseline_from_local", return_value=True
        ):
            result = orchestrator.ensure_baseline(interactive=True)

        assert result is True
        orchestrator.baseline_selector.select_baseline.assert_called_once()

    def test_baseline_enforcement_workflow(self, orchestrator):
        """Test complete workflow of enforcing baseline."""
        # Start with no baseline
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=None)

        # Ensure baseline with LOCAL strategy
        with patch.object(
            orchestrator, "_create_baseline_from_local", return_value=True
        ):
            assert orchestrator.ensure_baseline(
                strategy=BaselineStrategy.LOCAL, interactive=False
            )

        # Now baseline should exist (via saved state)
        baseline_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Test",
        )
        state = SyncState(
            last_sync=datetime.now(timezone.utc),
            backend="test",
        )
        state.issues["issue-1"] = baseline_state
        orchestrator.state_manager.load_sync_state = MagicMock(return_value=state)

        # Second ensure_baseline should return True without creating
        assert orchestrator.ensure_baseline(interactive=False) is True
