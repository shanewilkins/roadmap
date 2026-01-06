"""Tests for GitSyncMonitor - change detection and sync functionality."""

from unittest.mock import Mock

import pytest

from roadmap.adapters.git.sync_monitor import GitSyncMonitor


class TestGitSyncMonitorChangeDetection:
    """Test change detection via git diff."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a GitSyncMonitor instance for testing."""
        return GitSyncMonitor(repo_path=tmp_path)

    def test_detect_changes_not_in_git_repo(self, monitor):
        """Should return empty dict if not in a git repository."""
        # GitCommandExecutor.is_git_repository() returns False for tmp_path
        changes = monitor.detect_changes()
        assert changes == {}

    def test_detect_changes_no_commits(self, monitor):
        """Should return empty dict if unable to get current commit."""
        monitor.git_executor.is_git_repository = Mock(return_value=True)
        monitor.git_executor.run = Mock(return_value=None)

        changes = monitor.detect_changes()
        assert changes == {}

    def test_detect_changes_already_synced(self, monitor):
        """Should return empty dict if already synced to current commit."""
        current_commit = "abc123def456"

        monitor.git_executor.is_git_repository = Mock(return_value=True)
        monitor.git_executor.run = Mock(return_value=current_commit)

        # Save the sync state
        monitor._cached_last_synced_commit = current_commit
        monitor._cached_current_commit = current_commit

        changes = monitor.detect_changes()
        assert changes == {}

    def test_detect_changes_first_sync_no_previous(self, monitor):
        """Should get all files on first sync when no previous commit exists."""
        current_commit = "abc123def456"
        all_files_output = ".roadmap/issues/issue-1.yaml\n.roadmap/issues/issue-2.yaml"

        monitor.git_executor.is_git_repository = Mock(return_value=True)

        def git_run_side_effect(args):
            if "rev-parse" in args:
                return current_commit
            if "ls-files" in args:
                return all_files_output
            return ""

        monitor.git_executor.run = Mock(side_effect=git_run_side_effect)

        changes = monitor.detect_changes()

        assert len(changes) == 2
        assert changes[".roadmap/issues/issue-1.yaml"] == "added"
        assert changes[".roadmap/issues/issue-2.yaml"] == "added"

    def test_detect_changes_with_diffs(self, monitor):
        """Should detect modified, added, and deleted files."""
        current_commit = "abc123def456"
        last_synced = "xyz789uvw012"

        monitor.git_executor.is_git_repository = Mock(return_value=True)
        monitor.git_executor.run = Mock(return_value=current_commit)
        monitor._cached_last_synced_commit = last_synced
        monitor._cached_current_commit = current_commit

        # Mock _get_changed_files to return specific changes
        monitor._get_changed_files = Mock(
            return_value={
                ".roadmap/issues/issue-1.yaml": "modified",
                ".roadmap/issues/issue-2.yaml": "added",
                ".roadmap/issues/issue-3.yaml": "deleted",
            }
        )

        changes = monitor.detect_changes()

        assert len(changes) == 3
        assert changes[".roadmap/issues/issue-1.yaml"] == "modified"
        assert changes[".roadmap/issues/issue-2.yaml"] == "added"
        assert changes[".roadmap/issues/issue-3.yaml"] == "deleted"

    def test_detect_changes_ignores_non_issue_files(self, monitor):
        """Should ignore changes to non-.roadmap/issues/ files."""
        current_commit = "abc123def456"
        last_synced = "xyz789uvw012"

        monitor.git_executor.is_git_repository = Mock(return_value=True)
        monitor.git_executor.run = Mock(return_value=current_commit)
        monitor._cached_last_synced_commit = last_synced
        monitor._cached_current_commit = current_commit

        # Mock _get_changed_files with mixed files
        monitor._get_changed_files = Mock(
            return_value={
                ".roadmap/issues/issue-1.yaml": "modified",
                # Non-issue files filtered out by _get_changed_files
            }
        )

        changes = monitor.detect_changes()

        assert len(changes) == 1
        assert ".roadmap/issues/issue-1.yaml" in changes
        assert "README.md" not in changes
        assert "pyproject.toml" not in changes


class TestGitSyncMonitorFileChangeParsing:
    """Test parsing of git diff output."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a GitSyncMonitor instance for testing."""
        return GitSyncMonitor(repo_path=tmp_path)

    def test_parse_git_diff_modified(self, monitor):
        """Should parse modified status correctly."""
        monitor.git_executor.run = Mock(return_value="M\t.roadmap/issues/issue-1.yaml")

        changes = monitor._get_changed_files("abc123")

        assert len(changes) == 1
        assert changes[".roadmap/issues/issue-1.yaml"] == "modified"

    def test_parse_git_diff_added(self, monitor):
        """Should parse added status correctly."""
        monitor.git_executor.run = Mock(return_value="A\t.roadmap/issues/issue-2.yaml")

        changes = monitor._get_changed_files("abc123")

        assert len(changes) == 1
        assert changes[".roadmap/issues/issue-2.yaml"] == "added"

    def test_parse_git_diff_deleted(self, monitor):
        """Should parse deleted status correctly."""
        monitor.git_executor.run = Mock(return_value="D\t.roadmap/issues/issue-3.yaml")

        changes = monitor._get_changed_files("abc123")

        assert len(changes) == 1
        assert changes[".roadmap/issues/issue-3.yaml"] == "deleted"

    def test_parse_git_diff_multiple(self, monitor):
        """Should parse multiple files in one diff."""
        diff_output = (
            "M\t.roadmap/issues/issue-1.yaml\n"
            "A\t.roadmap/issues/issue-2.yaml\n"
            "D\t.roadmap/issues/issue-3.yaml"
        )
        monitor.git_executor.run = Mock(return_value=diff_output)

        changes = monitor._get_changed_files("abc123")

        assert len(changes) == 3
        assert changes[".roadmap/issues/issue-1.yaml"] == "modified"
        assert changes[".roadmap/issues/issue-2.yaml"] == "added"
        assert changes[".roadmap/issues/issue-3.yaml"] == "deleted"

    def test_parse_git_diff_with_spaces_in_filenames(self, monitor):
        """Should handle filenames with spaces."""
        diff_output = "M\t.roadmap/issues/issue with spaces.yaml"
        monitor.git_executor.run = Mock(return_value=diff_output)

        changes = monitor._get_changed_files("abc123")

        assert len(changes) == 1
        assert ".roadmap/issues/issue with spaces.yaml" in changes

    def test_parse_git_diff_filters_non_issue_files(self, monitor):
        """Should filter out non-.roadmap/issues/ files."""
        diff_output = (
            "M\t.roadmap/issues/issue-1.yaml\n"
            "M\tREADME.md\n"
            "A\t.roadmap/projects/project-1.yaml\n"
            "D\tpyproject.toml"
        )
        monitor.git_executor.run = Mock(return_value=diff_output)

        changes = monitor._get_changed_files("abc123")

        # Should only have the issue file
        assert len(changes) == 1
        assert ".roadmap/issues/issue-1.yaml" in changes

    def test_archive_issues_files_included(self, monitor):
        """Should include .roadmap/archive/issues/ files."""
        diff_output = (
            "M\t.roadmap/issues/issue-1.yaml\n"
            "D\t.roadmap/archive/issues/archived-1.yaml"
        )
        monitor.git_executor.run = Mock(return_value=diff_output)

        changes = monitor._get_changed_files("abc123")

        assert len(changes) == 2
        assert changes[".roadmap/issues/issue-1.yaml"] == "modified"
        assert changes[".roadmap/archive/issues/archived-1.yaml"] == "deleted"


class TestGitSyncMonitorSyncState:
    """Test sync state tracking."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a GitSyncMonitor instance for testing."""
        return GitSyncMonitor(repo_path=tmp_path)

    def test_save_and_retrieve_last_synced_commit(self, monitor):
        """Should save and retrieve last synced commit from file."""
        current_commit = "abc123def456"
        monitor.git_executor.run = Mock(return_value=current_commit)

        # Save
        assert monitor._save_last_synced_commit() is True

        # Clear cache
        monitor.clear_cache()

        # Retrieve
        retrieved = monitor._get_last_synced_commit()
        assert retrieved == current_commit

    def test_get_last_synced_commit_file_not_found(self, monitor):
        """Should return None if no sync metadata file exists."""
        commit = monitor._get_last_synced_commit()
        assert commit is None

    def test_get_last_synced_commit_uses_cache(self, monitor):
        """Should use cached value if available."""
        expected = "cached123"
        monitor._cached_last_synced_commit = expected

        commit = monitor._get_last_synced_commit()
        assert commit == expected

    def test_get_current_commit_uses_cache(self, monitor):
        """Should use cached current commit."""
        expected = "current456"
        monitor._cached_current_commit = expected

        commit = monitor._get_current_commit()
        assert commit == expected

    def test_clear_cache(self, monitor):
        """Should clear all cached commits."""
        monitor._cached_last_synced_commit = "cached123"
        monitor._cached_current_commit = "current456"

        monitor.clear_cache()

        assert monitor._cached_last_synced_commit is None
        assert monitor._cached_current_commit is None


class TestGitSyncMonitorDatabaseSync:
    """Test database sync functionality."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a GitSyncMonitor instance with mock state manager."""
        monitor = GitSyncMonitor(repo_path=tmp_path)
        monitor.state_manager = Mock()
        monitor.git_executor.run = Mock(return_value="abc123def456")
        return monitor

    def test_sync_to_database_without_state_manager(self, tmp_path):
        """Should return False if no state manager configured."""
        monitor = GitSyncMonitor(repo_path=tmp_path)
        monitor.state_manager = None

        result = monitor.sync_to_database({".roadmap/issues/issue-1.yaml": "modified"})

        assert result is False

    def test_sync_to_database_empty_changes(self, monitor):
        """Should return True for empty changes without doing work."""
        result = monitor.sync_to_database({})
        assert result is True

    def test_sync_to_database_updates_sync_state(self, monitor):
        """Should save sync state after successful sync."""
        changes = {
            ".roadmap/issues/issue-1.yaml": "modified",
            ".roadmap/issues/issue-2.yaml": "added",
        }

        result = monitor.sync_to_database(changes)

        # In Phase 1, should succeed (just save state)
        assert result is True

        # Should have saved the commit
        monitor.clear_cache()
        last_synced = monitor._get_last_synced_commit()
        assert last_synced is not None

    def test_sync_to_database_handles_errors(self, monitor):
        """Should handle errors during sync gracefully."""
        monitor._save_last_synced_commit = Mock(side_effect=Exception("DB error"))

        changes = {".roadmap/issues/issue-1.yaml": "modified"}
        result = monitor.sync_to_database(changes)

        # Should return False but not raise
        assert result is False


class TestGitSyncMonitorIsIssuesFile:
    """Test file path filtering."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a GitSyncMonitor instance for testing."""
        return GitSyncMonitor(repo_path=tmp_path)

    def test_is_issues_file_regular_issue(self, monitor):
        """Should identify .roadmap/issues/ files."""
        assert monitor._is_issues_file(".roadmap/issues/issue-1.yaml") is True

    def test_is_issues_file_archived_issue(self, monitor):
        """Should identify .roadmap/archive/issues/ files."""
        assert (
            monitor._is_issues_file(".roadmap/archive/issues/archived-1.yaml") is True
        )

    def test_is_issues_file_not_issues_file(self, monitor):
        """Should reject non-.roadmap/issues/ files."""
        assert monitor._is_issues_file("README.md") is False
        assert monitor._is_issues_file(".roadmap/projects/project-1.yaml") is False
        assert monitor._is_issues_file(".roadmap/milestones/milestone-1.yaml") is False
        assert monitor._is_issues_file("pyproject.toml") is False

    def test_is_issues_file_nested_in_issues(self, monitor):
        """Should handle nested files within .roadmap/issues/."""
        assert monitor._is_issues_file(".roadmap/issues/subdir/issue.yaml") is True
