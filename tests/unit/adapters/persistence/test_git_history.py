"""Unit tests for git history utilities.

Tests cover:
- Getting file content at various git states
- Finding commits by timestamp
- Error handling for non-git directories
- Edge cases (empty repo, file not found, etc.)
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from roadmap.adapters.persistence.git_history import (
    FileNotFound,
    GitHistoryError,
    NotAGitRepository,
    find_commit_at_time,
    get_changed_files_since_commit,
    get_file_at_commit,
    get_file_at_head,
    get_file_at_timestamp,
    get_last_modified_time,
    get_repository_root,
    is_git_repository,
)


class TestFindCommitAtTime:
    """Test finding commits by timestamp."""

    def test_find_commit_with_datetime(self, git_run_command_mocked):
        """Test finding commit with datetime object."""
        git_run_command_mocked.return_value = "abc123def456 2026-01-03T10:30:00+00:00"

        timestamp = datetime(2026, 1, 3, 10, 30, 0)
        result = find_commit_at_time(timestamp)

        assert result == "abc123def456"
        git_run_command_mocked.assert_called_once()

    def test_find_commit_with_iso_string(self, git_run_command_mocked):
        """Test finding commit with ISO 8601 timestamp string."""
        git_run_command_mocked.return_value = "xyz789 2026-01-03T10:30:00+00:00"

        result = find_commit_at_time("2026-01-03T10:30:00+00:00")

        assert result == "xyz789"

    def test_find_commit_with_file_path(self, git_run_command_mocked):
        """Test finding commits that affected a specific file."""
        git_run_command_mocked.return_value = "file123 2026-01-03T10:30:00+00:00"

        result = find_commit_at_time(
            datetime(2026, 1, 3, 10, 30, 0),
            file_path="src/example.py",
        )

        assert result == "file123"
        args = git_run_command_mocked.call_args[0][0]
        assert "src/example.py" in args

    def test_find_commit_no_commits_returns_first(self, git_run_command_mocked):
        """Test fallback to first commit when no commits before timestamp."""
        # First call returns empty (no commits before timestamp)
        # Second call returns first commit
        git_run_command_mocked.side_effect = ["", "first000"]

        result = find_commit_at_time(datetime.now(UTC))

        assert result == "first000"
        assert git_run_command_mocked.call_count == 2

    def test_find_commit_invalid_timestamp_format(self, git_run_command_mocked):
        """Test error handling for invalid timestamp format."""
        with pytest.raises(GitHistoryError):
            find_commit_at_time("not-a-valid-timestamp")


class TestGetFileAtCommit:
    """Test retrieving file content at specific commits."""

    def test_get_file_at_commit(self, git_run_command_mocked):
        """Test retrieving file content at commit."""
        git_run_command_mocked.return_value = "file content here\nline 2"

        result = get_file_at_commit("path/to/file.md", "abc123")

        assert result == "file content here\nline 2"
        git_run_command_mocked.assert_called_once()

    def test_get_file_at_commit_not_found(self, git_run_command_mocked):
        """Test error when file not found at commit."""
        git_run_command_mocked.side_effect = GitHistoryError(
            "does not exist in commit abc123"
        )

        with pytest.raises(FileNotFound):
            get_file_at_commit("missing.md", "abc123")

    def test_get_file_at_head(self, git_run_command_mocked):
        """Test retrieving file from HEAD."""
        git_run_command_mocked.return_value = "current content"

        result = get_file_at_head("file.md")

        assert result == "current content"
        # Should call git show HEAD:file.md
        args = git_run_command_mocked.call_args[0][0]
        assert "HEAD" in args[1]


class TestGetFileAtTimestamp:
    """Test retrieving file at specific timestamp."""

    @patch("roadmap.adapters.persistence.git_history.get_file_at_commit")
    @patch("roadmap.adapters.persistence.git_history.find_commit_at_time")
    def test_get_file_at_timestamp(self, mock_find, mock_get):
        """Test getting file at timestamp."""
        mock_find.return_value = "commit123"
        mock_get.return_value = "baseline content"

        result = get_file_at_timestamp("issue.md", datetime(2026, 1, 3, 10, 0, 0))

        assert result == "baseline content"
        mock_find.assert_called_once()
        mock_get.assert_called_once_with("issue.md", "commit123", ".")

    @patch("roadmap.adapters.persistence.git_history.get_file_at_commit")
    @patch("roadmap.adapters.persistence.git_history.find_commit_at_time")
    def test_get_file_at_timestamp_file_not_found(self, mock_find, mock_get):
        """Test error when file not found at timestamp."""
        mock_find.return_value = "commit123"
        mock_get.side_effect = FileNotFound("File not found")

        with pytest.raises(FileNotFound):
            get_file_at_timestamp("missing.md", datetime.now(UTC))

    @patch("roadmap.adapters.persistence.git_history.get_file_at_commit")
    @patch("roadmap.adapters.persistence.git_history.find_commit_at_time")
    def test_get_file_at_timestamp_with_string(self, mock_find, mock_get):
        """Test getting file at timestamp with ISO string."""
        mock_find.return_value = "abc123"
        mock_get.return_value = "content"

        result = get_file_at_timestamp("file.md", "2026-01-03T10:00:00Z")

        assert result == "content"


class TestGetLastModifiedTime:
    """Test getting file modification time."""

    def test_get_last_modified_time(self, git_run_command_mocked):
        """Test getting last modification time."""
        git_run_command_mocked.return_value = "2026-01-03T10:30:45+00:00"

        result = get_last_modified_time("file.md")

        assert isinstance(result, datetime)
        assert result.year == 2026
        git_run_command_mocked.assert_called_once()

    def test_get_last_modified_time_not_in_history(self, git_run_command_mocked):
        """Test when file not in git history."""
        git_run_command_mocked.return_value = ""

        result = get_last_modified_time("new_file.md")

        assert result is None

    def test_get_last_modified_time_error(self, git_run_command_mocked):
        """Test error handling."""
        git_run_command_mocked.side_effect = GitHistoryError("git command failed")

        with pytest.raises(GitHistoryError):
            get_last_modified_time("file.md")


class TestRepositoryChecks:
    """Test repository detection and root finding."""

    def test_is_git_repository_true(self, git_run_command_mocked):
        """Test detecting valid git repository."""
        git_run_command_mocked.return_value = ".git"

        result = is_git_repository("/some/path")

        assert result is True

    def test_is_git_repository_false(self, git_run_command_mocked):
        """Test detecting non-git directory."""
        git_run_command_mocked.side_effect = NotAGitRepository("not a repo")

        result = is_git_repository("/some/path")

        assert result is False

    def test_get_repository_root(self, git_run_command_mocked):
        """Test getting repository root."""
        git_run_command_mocked.return_value = "/home/user/projects/roadmap"

        result = get_repository_root("/home/user/projects/roadmap/src")

        assert result == "/home/user/projects/roadmap"

    def test_get_repository_root_not_git_repo(self, git_run_command_mocked):
        """Test error when not in git repository."""
        git_run_command_mocked.side_effect = NotAGitRepository("not a repo")

        with pytest.raises(NotAGitRepository):
            get_repository_root("/not/a/repo")


class TestGetChangedFiles:
    """Test getting changed files since reference."""

    def test_get_changed_files_since_commit(self, git_run_command_mocked):
        """Test getting changed files list."""
        git_run_command_mocked.return_value = "file1.md\nfile2.py\ndir/file3.txt"

        result = get_changed_files_since_commit("HEAD~1")

        assert len(result) == 3
        assert "file1.md" in result
        assert "file2.py" in result
        assert "dir/file3.txt" in result

    def test_get_changed_files_no_changes(self, git_run_command_mocked):
        """Test when no files changed."""
        git_run_command_mocked.return_value = ""

        result = get_changed_files_since_commit("HEAD")

        assert result == set()

    def test_get_changed_files_custom_ref(self, git_run_command_mocked):
        """Test with custom git reference."""
        git_run_command_mocked.return_value = "changed.md"

        result = get_changed_files_since_commit("main")

        assert "changed.md" in result
        args = git_run_command_mocked.call_args[0][0]
        assert "main" in args


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_git_not_found(self, git_run_command_mocked):
        """Test handling when git is not in PATH."""
        git_run_command_mocked.side_effect = GitHistoryError("Git not found in PATH")

        with pytest.raises(GitHistoryError):
            find_commit_at_time(datetime.now(UTC))

    def test_not_git_repository_error(self, git_run_command_mocked):
        """Test handling of not-a-git-repository error."""
        git_run_command_mocked.side_effect = NotAGitRepository("Not in a repo")

        with pytest.raises(NotAGitRepository):
            get_file_at_timestamp("file.md", datetime.now(UTC))

    def test_git_history_error_creation(self, git_run_command_mocked):
        """Test GitHistoryError exception."""
        error = GitHistoryError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)
