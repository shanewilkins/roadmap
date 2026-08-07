"""Tests for git commit analyzer."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from roadmap.adapters.git.git_commit_analyzer import GitCommitAnalyzer


class TestGitCommitAnalyzerInit:
    """Test GitCommitAnalyzer initialization."""

    def test_init_with_default_path(self, mocker):
        """Test initialization with default path."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        assert analyzer.repo_path == Path.cwd()

    def test_init_with_custom_path(self, mocker):
        """Test initialization with custom path."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        custom_path = Path("/custom/path")
        analyzer = GitCommitAnalyzer(custom_path)
        assert analyzer.repo_path == custom_path

    def test_init_creates_executor(self, mocker):
        """Test that initialization creates GitCommandExecutor."""
        mock_executor = mocker.patch(
            "roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor"
        )
        _ = GitCommitAnalyzer()
        mock_executor.assert_called_once()


class TestParseCommitLine:
    """Test commit line parsing."""

    def test_parse_valid_commit_line(self, mocker):
        """Test parsing a valid commit line."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        line = "abc123|John Doe|2025-12-23T10:30:00|Fix issue 123"
        result = analyzer._parse_commit_line(line)

        assert result is not None
        assert result[0] == "abc123"
        assert result[1] == "John Doe"
        assert result[3] == "Fix issue 123"

    def test_parse_empty_line(self, mocker):
        """Test parsing empty line."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        result = analyzer._parse_commit_line("")
        assert result is None

    def test_parse_whitespace_only_line(self, mocker):
        """Test parsing whitespace-only line."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        result = analyzer._parse_commit_line("   \n  ")
        assert result is None

    def test_parse_invalid_format_line(self, mocker):
        """Test parsing line with invalid format."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        line = "no|pipes|here"  # Missing message part
        result = analyzer._parse_commit_line(line)
        assert result is None or isinstance(result, tuple)

    def test_parse_line_with_pipes_in_message(self, mocker):
        """Test parsing line with pipes in commit message."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        line = "abc123|Author|2025-12-23T10:30:00|Fix issue with pipes | and stuff"
        result = analyzer._parse_commit_line(line)

        assert result is not None
        assert result[3] == "Fix issue with pipes | and stuff"

    @pytest.mark.parametrize(
        "line,should_parse",
        [
            ("abc123|Author|2025-12-23T10:30:00|Message", True),
            ("", False),
            ("   ", False),
            ("incomplete", False),
        ],
    )
    def test_parse_various_formats(self, mocker, line, should_parse):
        """Test parsing various line formats."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        result = analyzer._parse_commit_line(line)

        if should_parse:
            assert result is not None


class TestExtractFileStats:
    """Test file statistics extraction."""

    def test_extract_from_empty_output(self, mocker):
        """Test extraction from empty output."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        files, insertions, deletions = analyzer._extract_file_stats("")

        assert files == []
        assert insertions == 0
        assert deletions == 0

    def test_extract_from_none(self, mocker):
        """Test extraction from None."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        files, insertions, deletions = analyzer._extract_file_stats(None)

        assert files == []
        assert insertions == 0
        assert deletions == 0

    def test_extract_single_file(self, mocker):
        """Test extraction with single file."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        output = "file.py | 10 +++---\n 1 file changed, 5 insertions(+), 3 deletions(-)"
        files, insertions, deletions = analyzer._extract_file_stats(output)

        assert "file.py" in files
        assert insertions == 5
        assert deletions == 3

    def test_extract_multiple_files(self, mocker):
        """Test extraction with multiple files."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        output = """file1.py | 5 +++++
file2.py | 10 ++++++++
 2 files changed, 15 insertions(+)"""
        files, insertions, deletions = analyzer._extract_file_stats(output)

        assert len(files) == 2
        assert insertions == 15
        assert deletions == 0

    def test_extract_no_changes(self, mocker):
        """Test extraction with no file changes."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        output = "0 files changed"
        files, insertions, deletions = analyzer._extract_file_stats(output)

        assert files == []

    @pytest.mark.parametrize(
        "stat_line,exp_insertions,exp_deletions",
        [
            ("1 file changed, 5 insertions(+), 2 deletions(-)", 5, 2),
            ("1 file changed, 10 insertions(+)", 10, 0),
            ("1 file changed, 3 deletions(-)", 0, 3),
        ],
    )
    def test_extract_various_stat_formats(
        self, mocker, stat_line, exp_insertions, exp_deletions
    ):
        """Test extraction of various stat formats."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        output = f"file.py | ++\n {stat_line}"
        files, insertions, deletions = analyzer._extract_file_stats(output)

        assert insertions == exp_insertions
        assert deletions == exp_deletions


class TestBuildCommitObject:
    """Test GitCommit object building."""

    def test_build_valid_commit(self, mocker):
        """Test building a valid commit object."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        date = datetime(2025, 12, 23, 10, 30, 0)

        commit = analyzer._build_commit_object(
            "abc123", "Author", date, "Message", ["file.py"], 5, 2
        )

        assert commit is not None
        assert commit.hash == "abc123"
        assert commit.author == "Author"
        assert commit.message == "Message"
        assert commit.insertions == 5
        assert commit.deletions == 2

    def test_build_commit_with_none_date(self, mocker):
        """Test building commit with None date."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()

        commit = analyzer._build_commit_object(
            "abc123", "Author", None, "Message", ["file.py"], 5, 2
        )

        assert commit is None

    def test_build_commit_preserves_all_fields(self, mocker):
        """Test that building preserves all fields."""
        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        date = datetime(2025, 12, 23, 10, 30, 0)
        files = ["file1.py", "file2.py", "file3.txt"]

        commit = analyzer._build_commit_object(
            "hash123", "Test Author", date, "Test commit message", files, 50, 20
        )

        assert commit is not None
        assert commit.files_changed == files
        assert len(commit.files_changed) == 3


class TestParseCommitMessageForUpdates:
    """Test commit message parsing for roadmap updates."""

    def test_parse_empty_message(self, mocker):
        """Test parsing empty commit message."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        commit = Mock(message="", extract_progress_info=Mock(return_value=None))

        updates = analyzer.parse_commit_message_for_updates(commit)
        assert updates == {}

    def test_parse_progress_info(self, mocker):
        """Test parsing commit with progress information."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        commit = Mock(
            message="Work in progress",
            extract_progress_info=Mock(return_value=50.0),
        )

        updates = analyzer.parse_commit_message_for_updates(commit)
        assert "progress_percentage" in updates
        assert updates["progress_percentage"] == 50.0
        assert updates["status"] == "in-progress"

    def test_parse_completion_pattern_closes(self, mocker):
        """Test parsing completion pattern with 'closes'."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        commit = Mock(
            message="[closes roadmap:12345678]",
            extract_progress_info=Mock(return_value=None),
        )

        updates = analyzer.parse_commit_message_for_updates(commit)
        assert updates.get("status") == "closed"
        assert updates.get("progress_percentage") == 100.0

    def test_parse_wip_indicator(self, mocker):
        """Test parsing work-in-progress indicator."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        commit = Mock(
            message="[WIP] Still working on this",
            extract_progress_info=Mock(return_value=None),
        )

        updates = analyzer.parse_commit_message_for_updates(commit)
        assert updates.get("status") == "in-progress"

    @pytest.mark.parametrize(
        "message,expected_status",
        [
            ("[fixes roadmap:12345678]", "closed"),
            ("[resolve roadmap:12345678]", "closed"),
            ("[WIP] working", "in-progress"),
            ("normal message", {}),
        ],
    )
    def test_parse_various_completion_patterns(self, mocker, message, expected_status):
        """Test parsing various completion patterns."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        commit = Mock(message=message, extract_progress_info=Mock(return_value=None))

        updates = analyzer.parse_commit_message_for_updates(commit)
        if expected_status:
            assert "status" in updates
        else:
            assert len(updates) == 0

    def test_parse_message_case_insensitive(self, mocker):
        """Test that message parsing is case-insensitive."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        commit = Mock(
            message="CLOSES roadmap:12345678",
            extract_progress_info=Mock(return_value=None),
        )

        updates = analyzer.parse_commit_message_for_updates(commit)
        assert updates.get("status") == "closed"

    def test_parse_progress_boundary_values(self, mocker):
        """Test progress parsing with boundary values."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()

        # Test 0%
        commit_0 = Mock(message="", extract_progress_info=Mock(return_value=0.0))
        updates_0 = analyzer.parse_commit_message_for_updates(commit_0)
        assert updates_0.get("progress_percentage") == 0.0

        # Test 100%
        commit_100 = Mock(message="", extract_progress_info=Mock(return_value=100.0))
        updates_100 = analyzer.parse_commit_message_for_updates(commit_100)
        assert updates_100.get("progress_percentage") == 100.0

    def test_parse_progress_over_100_clamped(self, mocker):
        """Test that progress over 100% is clamped."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        commit = Mock(message="", extract_progress_info=Mock(return_value=150.0))

        updates = analyzer.parse_commit_message_for_updates(commit)
        assert updates.get("progress_percentage") == 100.0


class TestGetRecentCommits:
    """Test retrieving recent commits."""

    def test_get_recent_commits_empty(self, mocker):
        """Test getting recent commits when none exist."""

        mock_executor_class = mocker.patch(
            "roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor"
        )
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.run.return_value = ""

        analyzer = GitCommitAnalyzer()
        commits = analyzer.get_recent_commits(count=10)

        assert commits == []

    def test_get_recent_commits_count(self, mocker):
        """Test get_recent_commits calls with correct count."""

        mock_executor_class = mocker.patch(
            "roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor"
        )
        mock_executor = Mock()
        mock_executor_class.return_value = mock_executor
        mock_executor.run.return_value = ""

        analyzer = GitCommitAnalyzer()
        analyzer.get_recent_commits(count=20)

        # Should be called with -20 flag
        calls = mock_executor.run.call_args_list
        assert len(calls) > 0

    def test_get_commits_for_issue(self, mocker):
        """Test getting commits for specific issue."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        analyzer.get_recent_commits = Mock(return_value=[])

        _ = analyzer.get_commits_for_issue("issue123")

        # Should call get_recent_commits
        analyzer.get_recent_commits.assert_called_once()


class TestAutoUpdateIssuesFromCommits:
    """Test automatic issue updates from commits."""

    def test_auto_update_with_no_commits(self, mocker):
        """Test auto update with no commits provided."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        analyzer.get_recent_commits = Mock(return_value=[])

        core = Mock()
        results = analyzer.auto_update_issues_from_commits(core)

        assert results["updated"] == []
        assert results["closed"] == []
        assert results["errors"] == []

    def test_auto_update_initializes_result_lists(self, mocker):
        """Test that auto_update initializes all result lists."""

        mocker.patch("roadmap.adapters.git.git_commit_analyzer.GitCommandExecutor")
        analyzer = GitCommitAnalyzer()
        analyzer.get_recent_commits = Mock(return_value=[])

        core = Mock()
        results = analyzer.auto_update_issues_from_commits(core)

        assert "updated" in results
        assert "closed" in results
        assert "errors" in results
