"""Tests for SyncRetrievalOrchestrator with git-based baselines."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.adapters.sync.sync_retrieval_orchestrator import SyncRetrievalOrchestrator
from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState


@pytest.fixture
def mock_core():
    """Create mock RoadmapCore."""
    core = Mock()
    core.roadmap_dir = Path("/mock/roadmap")
    core.issues_dir = Path("/mock/roadmap/issues")
    core.issues = Mock()
    core.issues.list = Mock(return_value=[])
    core.db = Mock()
    return core


@pytest.fixture
def mock_backend():
    """Create mock backend."""
    backend = Mock()
    backend.__class__.__name__ = "MockBackend"
    return backend


def _setup_orchestrator_state_manager(orchestrator):
    """Helper to configure orchestrator's state_manager mocks."""
    orchestrator.state_manager = Mock()
    orchestrator.state_manager.load_sync_state = Mock(return_value=None)
    orchestrator.state_manager.get_sync_baseline = Mock(return_value=None)
    return orchestrator.state_manager


@pytest.fixture
def enhanced_orchestrator(mock_core, mock_backend):
    """Create SyncRetrievalOrchestrator."""
    with patch(
        "roadmap.adapters.sync.sync_retrieval_orchestrator.BaselineStateRetriever"
    ):
        orchestrator = SyncRetrievalOrchestrator(
            core=mock_core,
            backend=mock_backend,
        )
        # Inject mock state_manager after creation
        _setup_orchestrator_state_manager(orchestrator)
        return orchestrator


class TestSyncRetrievalOrchestratorInitialization:
    """Test SyncRetrievalOrchestrator initialization."""

    def test_initializes_with_baseline_retriever(self, enhanced_orchestrator):
        """Should initialize BaselineStateRetriever."""
        assert enhanced_orchestrator.baseline_retriever is not None
        assert hasattr(enhanced_orchestrator, "sync_metadata_cache")

    def test_issues_dir_computed_from_core(self, enhanced_orchestrator, mock_core):
        """Should compute issues directory from core."""
        result = enhanced_orchestrator.issues_dir
        assert result == Path("/mock/roadmap/issues")


class TestFindIssueFile:
    """Test issue file discovery."""

    def test_finds_issue_in_backlog(self, mock_core, tmp_path):
        """Should find issue file in backlog directory."""
        # Setup directory structure
        issues_dir = tmp_path / "issues"
        backlog_dir = issues_dir / "backlog"
        backlog_dir.mkdir(parents=True)

        # Create issue file
        issue_file = backlog_dir / "TASK-123-example.md"
        issue_file.write_text("# TASK-123")

        # Create orchestrator with mocked core
        mock_core.roadmap_dir = tmp_path
        with patch(
            "roadmap.adapters.sync.sync_retrieval_orchestrator.BaselineStateRetriever"
        ):
            orchestrator = SyncRetrievalOrchestrator(
                core=mock_core,
                backend=mock_backend,
            )
            _setup_orchestrator_state_manager(orchestrator)

        result = orchestrator._find_issue_file("TASK-123")
        assert result == issue_file

    def test_returns_none_when_not_found(self, mock_core, mock_backend, tmp_path):
        """Should return None when issue file not found."""
        issues_dir = tmp_path / "issues"
        issues_dir.mkdir(parents=True)

        mock_core.roadmap_dir = tmp_path
        with patch(
            "roadmap.adapters.sync.sync_retrieval_orchestrator.BaselineStateRetriever"
        ):
            orchestrator = SyncRetrievalOrchestrator(
                core=mock_core,
                backend=mock_backend,
            )
            _setup_orchestrator_state_manager(orchestrator)

        result = orchestrator._find_issue_file("NOTFOUND-999")
        assert result is None


class TestBuildBaselineStateFromGit:
    """Test git history baseline retrieval."""

    def test_returns_none_when_no_last_synced(self, enhanced_orchestrator):
        """Should return None when last_synced is None."""
        result = enhanced_orchestrator._build_baseline_state_from_git(None)
        assert result is None

    def test_reconstructs_baseline_from_git(self, enhanced_orchestrator, tmp_path):
        """Should reconstruct baseline from git history."""
        # Setup
        last_synced = datetime.now(UTC) - timedelta(hours=1)
        issue_id = "TASK-123"

        # Mock core.issues.list() - use list_all_including_archived for baseline
        mock_issue = Mock(spec=Issue)
        mock_issue.id = issue_id
        enhanced_orchestrator.core.issues.list_all_including_archived = Mock(
            return_value=[mock_issue]
        )

        # Mock _find_issue_file
        issue_file = tmp_path / "TASK-123-example.md"
        issue_file.write_text("# Test Issue")
        enhanced_orchestrator._find_issue_file = Mock(return_value=issue_file)

        # Mock baseline_retriever.get_local_baseline
        mock_baseline = IssueBaseState(
            id=issue_id,
            status=Status.TODO,
            title="Test Issue",
        )
        enhanced_orchestrator.baseline_retriever.get_local_baseline = Mock(
            return_value=mock_baseline
        )

        # Execute
        result = enhanced_orchestrator._build_baseline_state_from_git(last_synced)

        # Assert
        assert result is not None
        assert issue_id in result.base_issues
        assert result.base_issues[issue_id] == mock_baseline
        assert result.last_sync_time == last_synced


class TestGetBaselineState:
    """Test composite baseline state retrieval."""

    def test_returns_none_when_no_baselines_available(self, enhanced_orchestrator):
        """Should return None when no database, git or YAML baselines available."""
        enhanced_orchestrator.state_manager.get_sync_baseline = Mock(return_value=None)
        enhanced_orchestrator._build_baseline_state_from_git = Mock(return_value=None)
        enhanced_orchestrator._build_baseline_state_from_sync_metadata = Mock(
            return_value=None
        )
        enhanced_orchestrator.state_manager.load_sync_state = Mock(return_value=None)

        result = enhanced_orchestrator.get_baseline_state()

        assert result is None

    def test_uses_git_baseline_when_available(self, enhanced_orchestrator):
        """Should use git-based baseline when sync_metadata is available."""
        issue_id = "TASK-123"
        last_synced = datetime.now(UTC) - timedelta(hours=1)

        # Create mock baselines
        remote_baseline = IssueBaseState(
            id=issue_id,
            status=Status.TODO,
            title="Test",
        )
        remote_state = SyncState(
            last_sync_time=last_synced,
        )
        remote_state.base_issues[issue_id] = remote_baseline

        local_baseline = IssueBaseState(
            id=issue_id,
            status=Status.TODO,
            title="Test",
        )
        local_state = SyncState(
            last_sync_time=last_synced,
        )
        local_state.base_issues[issue_id] = local_baseline

        # Mock: database baseline not available (falls through to git)
        enhanced_orchestrator.core.db = Mock()
        enhanced_orchestrator.core.db.get_sync_baseline = Mock(return_value=None)

        # Mock: sync_metadata returns remote state, git returns local state
        with patch.object(
            enhanced_orchestrator,
            "_build_baseline_state_from_sync_metadata",
            return_value=remote_state,
        ):
            with patch.object(
                enhanced_orchestrator,
                "_build_baseline_state_from_git",
                return_value=local_state,
            ):
                result = enhanced_orchestrator.get_baseline_state()

                assert result is not None
                assert result.last_sync_time == last_synced
                assert result.base_issues[issue_id].status == Status.TODO


class TestCreateInitialBaseline:
    """Test initial baseline creation for first sync."""

    def test_creates_baseline_from_local_issues(self, enhanced_orchestrator):
        """Should create baseline from current local issues."""
        # Setup: Create some local issues
        issue1 = Issue(
            id="issue-1",
            title="First Issue",
            status=Status.TODO,
            content="Test issue 1",
            file_path=".roadmap/issues/issue-1.md",
        )
        issue2 = Issue(
            id="issue-2",
            title="Second Issue",
            status=Status.IN_PROGRESS,
            content="Test issue 2",
            file_path=".roadmap/issues/issue-2.md",
        )

        enhanced_orchestrator.core.issues.list_all_including_archived = Mock(
            return_value=[issue1, issue2]
        )

        # Mock baseline retriever
        base_state1 = IssueBaseState(
            id="issue-1",
            title="First Issue",
            status=Status.TODO,
            assignee=None,
            description="Test issue 1",
            labels=[],
        )
        base_state2 = IssueBaseState(
            id="issue-2",
            title="Second Issue",
            status=Status.IN_PROGRESS,
            assignee=None,
            description="Test issue 2",
            labels=[],
        )

        def get_baseline_from_file_side_effect(issue_file):
            """Return baseline based on filename."""
            filename = str(issue_file)
            return base_state1 if "issue-1" in filename else base_state2

        enhanced_orchestrator.baseline_retriever.get_baseline_from_file = Mock(
            side_effect=get_baseline_from_file_side_effect
        )

        # Mock issues_dir.exists() and issue file checks
        with patch("pathlib.Path.exists", return_value=True):
            baseline = enhanced_orchestrator._create_initial_baseline()

            assert baseline is not None
            assert len(baseline.base_issues) == 2
            assert "issue-1" in baseline.base_issues
            assert "issue-2" in baseline.base_issues
            assert baseline.base_issues["issue-1"].status == Status.TODO
            assert baseline.base_issues["issue-2"].status == Status.IN_PROGRESS

    def test_returns_empty_baseline_when_no_issues(self, enhanced_orchestrator):
        """Should return empty baseline when no local issues exist."""
        enhanced_orchestrator.core.issues.list = Mock(return_value=[])

        baseline = enhanced_orchestrator._create_initial_baseline()

        assert baseline is not None
        assert len(baseline.base_issues) == 0

    def test_handles_missing_issue_files(self, enhanced_orchestrator):
        """Should skip issues with missing files gracefully."""
        issue1 = Issue(
            id="issue-1",
            title="Existing Issue",
            status=Status.TODO,
            content="Test",
            file_path=".roadmap/issues/issue-1.md",
        )
        issue2 = Issue(
            id="issue-2",
            title="Missing Issue",
            status=Status.TODO,
            content="Test",
            file_path=".roadmap/issues/issue-2.md",
        )

        enhanced_orchestrator.core.issues.list_all_including_archived = Mock(
            return_value=[issue1, issue2]
        )

        base_state = IssueBaseState(
            id="issue-1",
            title="Existing Issue",
            status="todo",
            assignee=None,
            description="Test",
            labels=[],
        )

        enhanced_orchestrator.baseline_retriever.get_baseline_from_file = Mock(
            return_value=base_state
        )

        # Mock exists to return True for issue-1 and False for issue-2
        def exists_side_effect(path_str=None):
            if "issue-1" in str(path_str):
                return True
            elif "issue-2" in str(path_str):
                return False
            return True

        with patch("pathlib.Path.exists", side_effect=exists_side_effect):
            baseline = enhanced_orchestrator._create_initial_baseline()

            # Should only have the existing issue
            assert baseline is not None
            assert "issue-1" in baseline.base_issues
