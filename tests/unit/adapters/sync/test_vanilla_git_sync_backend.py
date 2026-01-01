"""Unit tests for vanilla git sync backend implementation.

Tests the VanillaGitSyncBackend implementation of SyncBackendInterface.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.sync.backends.vanilla_git_sync_backend import (
    VanillaGitSyncBackend,
)
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import SyncConflict, SyncReport


class TestVanillaGitSyncBackendInit:
    """Test VanillaGitSyncBackend initialization."""

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_init_with_valid_git_repo(self, mock_run):
        """Test backend initializes in a valid git repo."""
        core = MagicMock()
        config = {}

        # Mock git command to return valid repo path
        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")

        backend = VanillaGitSyncBackend(core, config)

        assert backend.core is core
        assert backend.remote_name == "origin"
        assert backend.repo_path == Path("/path/to/repo")

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_init_with_custom_remote(self, mock_run):
        """Test backend initializes with custom remote name."""
        core = MagicMock()
        config = {"remote_name": "upstream"}

        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")

        backend = VanillaGitSyncBackend(core, config)

        assert backend.remote_name == "upstream"

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_init_not_in_git_repo_raises_error(self, mock_run):
        """Test backend raises ValueError if not in git repo."""
        core = MagicMock()
        config = {}

        # Mock git command to fail (not in repo)
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        with pytest.raises(ValueError, match="git repository"):
            VanillaGitSyncBackend(core, config)

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_init_git_not_available_raises_error(self, mock_run):
        """Test backend raises ValueError if git not available."""
        core = MagicMock()
        config = {}

        # Mock git command to raise FileNotFoundError
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(ValueError, match="git command"):
            VanillaGitSyncBackend(core, config)


class TestVanillaGitSyncBackendAuthenticate:
    """Test authenticate method."""

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_authenticate_success(self, mock_run):
        """Test authenticate succeeds with valid remote."""
        core = MagicMock()
        config = {}

        # Mock init
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init git check
            MagicMock(returncode=0),  # ls-remote
        ]

        backend = VanillaGitSyncBackend(core, config)
        result = backend.authenticate()

        assert result is True

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_authenticate_failure(self, mock_run):
        """Test authenticate fails with unreachable remote."""
        core = MagicMock()
        config = {}

        # Mock init and authentication failure
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            MagicMock(returncode=1),  # ls-remote fails
        ]

        backend = VanillaGitSyncBackend(core, config)
        result = backend.authenticate()

        assert result is False

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_authenticate_handles_exceptions(self, mock_run):
        """Test authenticate handles exceptions gracefully."""
        core = MagicMock()
        config = {}

        # Mock init success but auth raises exception
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            Exception("Network error"),  # ls-remote raises
        ]

        backend = VanillaGitSyncBackend(core, config)
        result = backend.authenticate()

        assert result is False


class TestVanillaGitSyncBackendGetIssues:
    """Test get_issues method."""

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    @patch("pathlib.Path.rglob")
    def test_get_issues_returns_dict(self, mock_rglob, mock_run):
        """Test get_issues returns a dictionary."""
        core = MagicMock()
        config = {}

        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")
        mock_rglob.return_value = []

        backend = VanillaGitSyncBackend(core, config)
        result = backend.get_issues()

        assert isinstance(result, dict)

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_get_issues_fetch_failure(self, mock_run):
        """Test get_issues returns empty dict on fetch failure."""
        core = MagicMock()
        config = {}

        # Mock init and fetch failure
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            MagicMock(returncode=1),  # fetch fails
        ]

        backend = VanillaGitSyncBackend(core, config)
        result = backend.get_issues()

        assert result == {}

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_get_issues_handles_exceptions(self, mock_run):
        """Test get_issues handles exceptions gracefully."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            Exception("IO Error"),  # fetch raises
        ]

        backend = VanillaGitSyncBackend(core, config)
        result = backend.get_issues()

        assert result == {}


class TestVanillaGitSyncBackendPushIssue:
    """Test push_issue method."""

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    @patch("pathlib.Path.rglob")
    def test_push_issue_returns_bool(self, mock_rglob, mock_run):
        """Test push_issue returns a boolean."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
        ]
        mock_rglob.return_value = []

        backend = VanillaGitSyncBackend(core, config)
        issue = Issue(title="Test Issue")

        result = backend.push_issue(issue)

        assert isinstance(result, bool)

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    @patch("pathlib.Path.rglob")
    def test_push_issue_no_issue_file(self, mock_rglob, mock_run):
        """Test push_issue returns False when issue file doesn't exist."""
        core = MagicMock()
        config = {}

        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")
        mock_rglob.return_value = []  # No issue files found

        backend = VanillaGitSyncBackend(core, config)
        issue = Issue(title="Test Issue")

        result = backend.push_issue(issue)

        assert result is False

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_push_issue_handles_exceptions(self, mock_run):
        """Test push_issue handles exceptions gracefully."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            Exception("Git error"),  # push raises
        ]

        backend = VanillaGitSyncBackend(core, config)
        issue = Issue(title="Test Issue")

        result = backend.push_issue(issue)

        assert result is False


class TestVanillaGitSyncBackendPushIssues:
    """Test push_issues method."""

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    @patch("pathlib.Path.rglob")
    def test_push_issues_returns_sync_report(self, mock_rglob, mock_run):
        """Test push_issues returns SyncReport."""
        core = MagicMock()
        config = {}

        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")
        mock_rglob.return_value = []

        backend = VanillaGitSyncBackend(core, config)
        issues = [Issue(title="Issue 1"), Issue(title="Issue 2")]

        result = backend.push_issues(issues)

        assert isinstance(result, SyncReport)

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_push_issues_handles_exceptions(self, mock_run):
        """Test push_issues handles exceptions gracefully."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            Exception("Error"),  # push raises
        ]

        backend = VanillaGitSyncBackend(core, config)
        issues = [Issue(title="Issue 1")]

        result = backend.push_issues(issues)

        assert isinstance(result, SyncReport)
        assert "push" in result.errors


class TestVanillaGitSyncBackendPullIssues:
    """Test pull_issues method."""

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_pull_issues_returns_sync_report(self, mock_run):
        """Test pull_issues returns SyncReport."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
        ]

        backend = VanillaGitSyncBackend(core, config)

        result = backend.pull_issues()

        assert isinstance(result, SyncReport)

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_pull_issues_fetch_failure(self, mock_run):
        """Test pull_issues handles fetch failure."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            MagicMock(returncode=1, stderr="Connection failed"),  # fetch fails
        ]

        backend = VanillaGitSyncBackend(core, config)

        result = backend.pull_issues()

        assert isinstance(result, SyncReport)
        assert "fetch" in result.errors

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_pull_issues_merge_conflict(self, mock_run):
        """Test pull_issues detects merge conflicts."""
        core = MagicMock()
        config = {}

        # Mock successful fetch, failed merge, and conflict detection
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            MagicMock(returncode=0),  # fetch succeeds
            MagicMock(returncode=1),  # merge fails (conflict)
            MagicMock(
                returncode=0, stdout=".roadmap/issues/abc12345-test.md\n"
            ),  # diff shows conflicts
        ]

        backend = VanillaGitSyncBackend(core, config)

        result = backend.pull_issues()

        assert isinstance(result, SyncReport)
        assert len(result.conflicts) > 0

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_pull_issues_handles_exceptions(self, mock_run):
        """Test pull_issues handles exceptions gracefully."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            Exception("IO Error"),  # pull raises
        ]

        backend = VanillaGitSyncBackend(core, config)

        result = backend.pull_issues()

        assert isinstance(result, SyncReport)
        assert "pull" in result.errors


class TestVanillaGitSyncBackendConflictResolution:
    """Test conflict resolution methods."""

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_get_conflict_resolution_options(self, mock_run):
        """Test get_conflict_resolution_options returns list."""
        core = MagicMock()
        config = {}

        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")

        backend = VanillaGitSyncBackend(core, config)
        conflict = SyncConflict(
            issue_id="test",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="merge_conflict",
        )

        options = backend.get_conflict_resolution_options(conflict)

        assert isinstance(options, list)
        assert "use_local" in options
        assert "use_remote" in options
        assert "abort_merge" in options

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_resolve_conflict_use_local(self, mock_run):
        """Test resolve_conflict with use_local strategy."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            MagicMock(returncode=0),  # checkout ours
            MagicMock(returncode=0),  # git add
        ]

        backend = VanillaGitSyncBackend(core, config)
        conflict = SyncConflict(
            issue_id="test",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="merge_conflict",
        )

        result = backend.resolve_conflict(conflict, "use_local")

        assert result is True

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_resolve_conflict_use_remote(self, mock_run):
        """Test resolve_conflict with use_remote strategy."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            MagicMock(returncode=0),  # checkout theirs
            MagicMock(returncode=0),  # git add
        ]

        backend = VanillaGitSyncBackend(core, config)
        conflict = SyncConflict(
            issue_id="test",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="merge_conflict",
        )

        result = backend.resolve_conflict(conflict, "use_remote")

        assert result is True

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_resolve_conflict_abort_merge(self, mock_run):
        """Test resolve_conflict with abort_merge strategy."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            MagicMock(returncode=0),  # merge abort
        ]

        backend = VanillaGitSyncBackend(core, config)
        conflict = SyncConflict(
            issue_id="test",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="merge_conflict",
        )

        result = backend.resolve_conflict(conflict, "abort_merge")

        assert result is True

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_resolve_conflict_invalid_strategy(self, mock_run):
        """Test resolve_conflict with invalid strategy."""
        core = MagicMock()
        config = {}

        mock_run.return_value = MagicMock(returncode=0, stdout="/path/to/repo\n")

        backend = VanillaGitSyncBackend(core, config)
        conflict = SyncConflict(
            issue_id="test",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="merge_conflict",
        )

        result = backend.resolve_conflict(conflict, "invalid_strategy")

        assert result is False

    @patch("roadmap.adapters.sync.backends.vanilla_git_sync_backend.subprocess.run")
    def test_resolve_conflict_handles_exceptions(self, mock_run):
        """Test resolve_conflict handles exceptions gracefully."""
        core = MagicMock()
        config = {}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/path/to/repo\n"),  # init
            Exception("Git error"),  # resolve raises
        ]

        backend = VanillaGitSyncBackend(core, config)
        conflict = SyncConflict(
            issue_id="test",
            local_version=Issue(title="Local"),
            remote_version={"title": "Remote"},
            conflict_type="merge_conflict",
        )

        result = backend.resolve_conflict(conflict, "use_local")

        assert result is False
