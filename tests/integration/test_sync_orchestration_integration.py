"""Integration tests for Phase C: GitHub backend integration with three-way merge.

Tests that:
1. Three-way merge is used in sync orchestrator
2. Sync state is persisted after successful sync
3. Base state is loaded for next sync
4. True conflicts are identified and flagged
5. Resolvable conflicts are auto-resolved
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest

from roadmap.adapters.sync.generic_sync_orchestrator import GenericSyncOrchestrator
from roadmap.core.domain.issue import Issue, Status
from roadmap.core.models.sync_state import SyncState, IssueBaseState
from roadmap.core.services.sync_state_manager import SyncStateManager
from roadmap.core.services.sync_conflict_resolver import SyncConflictResolver
from roadmap.core.services.sync.three_way_merger import ThreeWayMerger


@pytest.fixture
def temp_roadmap_dir(tmp_path):
    """Create a temporary .roadmap directory."""
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir(parents=True, exist_ok=True)
    return roadmap_dir


@pytest.fixture
def sync_state_manager(temp_roadmap_dir):
    """Create a SyncStateManager with temp directory."""
    return SyncStateManager(temp_roadmap_dir)


@pytest.fixture
def mock_core(tmp_path):
    """Create a mock RoadmapCore."""
    core = Mock()
    core.roadmap_dir = tmp_path / ".roadmap"
    core.roadmap_dir.mkdir(exist_ok=True)
    core.issues = Mock()
    return core


@pytest.fixture
def mock_backend():
    """Create a mock sync backend."""
    backend = Mock()
    backend.authenticate.return_value = True
    return backend


class TestThreeWayMergeIntegration:
    """Test three-way merge integration in orchestrator."""

    def test_orchestrator_uses_three_way_merger(self, mock_core, mock_backend):
        """Verify orchestrator creates and uses ThreeWayMerger."""
        orchestrator = GenericSyncOrchestrator(
            mock_core, mock_backend
        )
        
        assert isinstance(orchestrator.merger, ThreeWayMerger)
        assert orchestrator.merger is not None

    def test_sync_with_no_prior_state(self, mock_core, mock_backend):
        """Test sync when no prior sync state exists."""
        # Setup
        orchestrator = GenericSyncOrchestrator(mock_core, mock_backend)
        
        mock_core.issues.list.return_value = []
        mock_backend.get_issues.return_value = {}
        
        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)
        
        # Verify
        assert report.error is None
        assert report.conflicts_detected == 0

    def test_sync_with_clean_merge(self, mock_core, mock_backend, sync_state_manager):
        """Test sync with no conflicts (clean merge)."""
        # Create local issue
        local_issue = Mock(spec=Issue)
        local_issue.id = "issue-1"
        local_issue.status = Status.TODO
        local_issue.assignee = None
        local_issue.labels = []
        local_issue.content = "Test issue"
        
        # Setup orchestrator with merger
        orchestrator = GenericSyncOrchestrator(
            mock_core, mock_backend
        )
        
        mock_core.issues.list.return_value = [local_issue]
        mock_core.roadmap_dir = sync_state_manager.roadmap_dir
        
        # Remote has same issue, same state (clean)
        mock_backend.get_issues.return_value = {
            "issue-1": {
                "id": "issue-1",
                "status": "todo",
                "assignee": None,
                "labels": [],
                "content": "Test issue",
            }
        }
        
        # Execute dry-run
        report = orchestrator.sync_all_issues(dry_run=True)
        
        # Verify: no conflicts
        assert report.error is None
        assert report.conflicts_detected == 0

    def test_sync_state_persistence(self, mock_core, mock_backend, sync_state_manager):
        """Test that sync state is saved after successful sync."""
        # Create issues
        local_issue = Mock(spec=Issue)
        local_issue.id = "issue-1"
        local_issue.status = Status.IN_PROGRESS
        local_issue.assignee = Mock(name="alice")
        local_issue.labels = ["bug"]
        local_issue.content = "Test issue"
        local_issue.updated = datetime.now()
        
        # Setup
        orchestrator = GenericSyncOrchestrator(
            mock_core, mock_backend
        )
        orchestrator.state_manager = sync_state_manager
        
        mock_core.issues.list.return_value = [local_issue]
        mock_backend.get_issues.return_value = {
            "issue-1": {
                "id": "issue-1",
                "status": "in-progress",
                "assignee": "alice",
                "labels": ["bug"],
                "content": "Test issue",
            }
        }
        mock_backend.push_issues.return_value = None
        
        # Execute with apply
        report = orchestrator.sync_all_issues(dry_run=False)
        
        # Verify: sync state was saved
        assert sync_state_manager.state_file.exists()
        
        with open(sync_state_manager.state_file, "r") as f:
            saved_state = json.load(f)
        
        assert "issue-1" in saved_state["issues"]
        assert saved_state["issues"]["issue-1"]["status"] == "in-progress"

    def test_base_state_loaded_for_merge(self, mock_core, mock_backend, sync_state_manager):
        """Test that base state is loaded and used for three-way merge."""
        # Create previous sync state (base)
        base_state = SyncState(
            last_sync=datetime.now(),
            backend="github",
            issues={
                "issue-1": IssueBaseState(
                    id="issue-1",
                    status="todo",
                    assignee=None,
                    milestone=None,
                    description="Original",
                    labels=[],
                )
            }
        )
        
        # Save base state
        sync_state_manager.save_sync_state(base_state)
        
        # Create orchestrator
        orchestrator = GenericSyncOrchestrator(
            mock_core, mock_backend
        )
        orchestrator.state_manager = sync_state_manager
        
        # Local changed: status → in-progress
        local_issue = Mock(spec=Issue)
        local_issue.id = "issue-1"
        local_issue.status = Status.IN_PROGRESS
        local_issue.assignee = None
        local_issue.labels = []
        local_issue.content = "Original"
        
        mock_core.issues.list.return_value = [local_issue]
        
        # Remote changed: assignee → bob
        mock_backend.get_issues.return_value = {
            "issue-1": {
                "id": "issue-1",
                "status": "todo",
                "assignee": "bob",
                "labels": [],
                "content": "Original",
            }
        }
        
        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)
        
        # Verify: both changes should be accepted (no conflict since different fields)
        assert report.error is None
        assert report.conflicts_detected == 0  # No true conflicts


class TestConflictDetectionAndResolution:
    """Test conflict detection and resolution logic."""

    def test_true_conflict_detected(self, mock_core, mock_backend, sync_state_manager):
        """Test that true conflicts are detected correctly."""
        # Create base state
        base_state = SyncState(
            last_sync=datetime.now(),
            backend="github",
            issues={
                "issue-1": IssueBaseState(
                    id="issue-1",
                    status="todo",
                    assignee=None,
                    milestone=None,
                    description="Original",
                    labels=[],
                )
            }
        )
        sync_state_manager.save_sync_state(base_state)
        
        # Create orchestrator
        orchestrator = GenericSyncOrchestrator(
            mock_core, mock_backend
        )
        orchestrator.state_manager = sync_state_manager
        
        # Local changed: status → in-progress
        local_issue = Mock(spec=Issue)
        local_issue.id = "issue-1"
        local_issue.status = Status.IN_PROGRESS
        local_issue.assignee = None
        local_issue.labels = []
        local_issue.content = "Original"
        
        mock_core.issues.list.return_value = [local_issue]
        
        # Remote changed: status → done (CONFLICT!)
        mock_backend.get_issues.return_value = {
            "issue-1": {
                "id": "issue-1",
                "status": "done",
                "assignee": None,
                "labels": [],
                "content": "Original",
            }
        }
        
        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)
        
        # Verify: true conflict detected
        assert report.conflicts_detected > 0

    def test_auto_resolution_of_non_critical_field(self, mock_core, mock_backend, sync_state_manager):
        """Test that non-critical field conflicts are auto-resolved."""
        # Create base state with created_at
        base_state = SyncState(
            last_sync=datetime.now(),
            backend="github",
            issues={
                "issue-1": IssueBaseState(
                    id="issue-1",
                    status="todo",
                    assignee=None,
                    milestone=None,
                    description="Original",
                    labels=[],
                )
            }
        )
        sync_state_manager.save_sync_state(base_state)
        
        orchestrator = GenericSyncOrchestrator(
            mock_core, mock_backend
        )
        orchestrator.state_manager = sync_state_manager
        
        # Local: labels changed
        local_issue = Mock(spec=Issue)
        local_issue.id = "issue-1"
        local_issue.status = Status.TODO
        local_issue.assignee = None
        local_issue.labels = ["bug", "urgent"]  # Local added labels
        local_issue.content = "Original"
        
        mock_core.issues.list.return_value = [local_issue]
        
        # Remote: labels changed differently
        mock_backend.get_issues.return_value = {
            "issue-1": {
                "id": "issue-1",
                "status": "todo",
                "assignee": None,
                "labels": ["feature", "docs"],  # Remote added different labels
                "content": "Original",
            }
        }
        
        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)
        
        # Verify: should be merged (union) not marked as true conflict
        # Labels conflict should be auto-resolvable
        assert report.error is None


class TestSyncStateFileManagement:
    """Test sync state file creation and loading."""

    def test_sync_state_file_created(self, sync_state_manager):
        """Test that sync state file is created correctly."""
        # Create state
        state = SyncState(
            last_sync=datetime.now(),
            backend="github",
            issues={
                "issue-1": IssueBaseState(
                    id="issue-1",
                    status="todo",
                    assignee="alice",
                    milestone=None,
                    description="Test",
                    labels=["bug"],
                )
            }
        )
        
        # Save
        success = sync_state_manager.save_sync_state(state)
        
        # Verify
        assert success
        assert sync_state_manager.state_file.exists()

    def test_sync_state_file_loaded(self, sync_state_manager):
        """Test that sync state file is loaded correctly."""
        # Create and save state
        original = SyncState(
            last_sync=datetime.now(),
            backend="github",
            issues={
                "issue-1": IssueBaseState(
                    id="issue-1",
                    status="todo",
                    assignee="alice",
                    milestone=None,
                    description="Test",
                    labels=["bug"],
                )
            }
        )
        sync_state_manager.save_sync_state(original)
        
        # Load
        loaded = sync_state_manager.load_sync_state()
        
        # Verify
        assert loaded is not None
        assert loaded.backend == "github"
        assert "issue-1" in loaded.issues
        assert loaded.issues["issue-1"].assignee == "alice"

    def test_missing_sync_state_returns_none(self, sync_state_manager):
        """Test that loading nonexistent state returns None."""
        loaded = sync_state_manager.load_sync_state()
        
        assert loaded is None
