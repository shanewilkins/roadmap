"""Unit tests for baseline state retrieval.

Tests cover:
- Retrieving local baseline from git history
- Retrieving remote baseline from sync_metadata
- Error handling for missing files/metadata
- Field extraction from both sources
"""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from roadmap.adapters.persistence.parser.issue import IssueParser
from roadmap.core.domain import Issue, IssueType, Priority, Status
from roadmap.core.interfaces.parsers import IssueParserInterface
from roadmap.core.interfaces.persistence import PersistenceInterface
from roadmap.core.services.baseline.baseline_state_retriever import (
    BaselineRetrievalError,
    BaselineStateRetriever,
)


class TestGetLocalBaseline:
    """Test local baseline retrieval from git history."""

    def _make_retriever(
        self, mock_persistence=None, mock_parser=None, temp_dir_context=None
    ):
        """Create a BaselineStateRetriever with mock dependencies."""
        if mock_persistence is None:
            mock_persistence = MagicMock(spec=PersistenceInterface)
        if mock_parser is None:
            mock_parser = MagicMock(spec=IssueParserInterface)

        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            return (
                BaselineStateRetriever(issues_dir, mock_persistence),
                mock_persistence,
                mock_parser,
                issues_dir,
            )

    def test_get_local_baseline_success(self, temp_dir_context):
        """Test successfully retrieving local baseline."""
        retriever, mock_persistence, mock_parser, issues_dir = self._make_retriever(
            temp_dir_context=temp_dir_context
        )

        # Create file content with metadata
        issue_content = """---
id: issue1
title: Test Issue
status: in-progress
priority: high
assignee: john@example.com
milestone: v1.0
description: Original description
labels:
  - bug
  - urgent
created: 2026-01-01T10:00:00+00:00
updated: 2026-01-02T11:00:00+00:00
---

Issue content here"""

        mock_persistence.get_file_at_timestamp.return_value = issue_content

        # Mock parser to return parsed issue
        mock_issue = MagicMock()
        mock_issue.id = "issue1"
        mock_issue.title = "Test Issue"
        mock_issue.status = Status.IN_PROGRESS
        mock_issue.assignee = "john@example.com"
        mock_issue.milestone = "v1.0"
        mock_issue.labels = ["bug", "urgent"]
        mock_issue.headline = None
        mock_issue.content = "Issue content here"

        mock_parser.parse_issue_file.return_value = mock_issue

        issue_file = issues_dir / "issue1.md"
        last_synced = datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC)

        baseline = retriever.get_local_baseline(issue_file, last_synced)

        assert baseline is not None
        assert baseline.id == "issue1"
        assert baseline.title == "Test Issue"
        assert baseline.status == "in-progress"
        assert baseline.assignee == "john@example.com"
        assert "bug" in baseline.labels

    def test_get_local_baseline_file_not_found(self, temp_dir_context):
        """Test when file didn't exist at baseline time."""
        from roadmap.core.interfaces.persistence import FileNotFound

        retriever, mock_persistence, mock_parser, issues_dir = self._make_retriever(
            temp_dir_context=temp_dir_context
        )

        mock_persistence.get_file_at_timestamp.side_effect = FileNotFound(
            "File not found"
        )

        issue_file = issues_dir / "issue1.md"
        result = retriever.get_local_baseline(issue_file, datetime.now(UTC))

        assert result is None

    def test_get_local_baseline_git_error(self, temp_dir_context):
        """Test handling of git errors."""
        from roadmap.core.interfaces.persistence import GitHistoryError

        retriever, mock_persistence, mock_parser, issues_dir = self._make_retriever(
            temp_dir_context=temp_dir_context
        )

        mock_persistence.get_file_at_timestamp.side_effect = GitHistoryError(
            "Git command failed"
        )

        issue_file = issues_dir / "issue1.md"

        with pytest.raises(BaselineRetrievalError):
            retriever.get_local_baseline(issue_file, datetime.now(UTC))


class TestGetRemoteBaseline:
    """Test remote baseline retrieval from sync_metadata."""

    def _make_retriever(
        self, mock_persistence=None, mock_parser=None, temp_dir_context=None
    ):
        """Create a BaselineStateRetriever with mock dependencies."""
        if mock_persistence is None:
            mock_persistence = MagicMock(spec=PersistenceInterface)
        if mock_parser is None:
            mock_parser = MagicMock(spec=IssueParserInterface)

        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            return (
                BaselineStateRetriever(issues_dir, mock_persistence),
                mock_persistence,
                mock_parser,
                issues_dir,
            )

    def test_get_remote_baseline_success(self, temp_dir_context):
        """Test successfully retrieving remote baseline from sync_metadata."""
        retriever, mock_persistence, mock_parser, issues_dir = self._make_retriever(
            temp_dir_context=temp_dir_context
        )

        # Create issue with sync_metadata
        issue = Issue(
            id="issue1",
            title="Test Issue",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
            assignee="john@example.com",
            milestone="v1.0",
            content="Local description",
        )

        issue_file = issues_dir / "issue1.md"

        sync_metadata = {
            "last_synced": "2026-01-02T10:00:00+00:00",
            "remote_state": {
                "id": "issue1",
                "title": "Test Issue",
                "status": "open",  # Remote status
                "assignee": "jane@example.com",  # Different assignee
                "milestone": "v1.0",
                "headline": "Remote description",
                "labels": ["bug"],
                "updated_at": "2026-01-02T09:00:00+00:00",
            },
        }

        IssueParser.save_issue_file(issue, issue_file, sync_metadata=sync_metadata)

        baseline = retriever.get_remote_baseline(issue_file)

        assert baseline is not None
        assert baseline.id == "issue1"
        assert baseline.title == "Test Issue"
        assert baseline.status == "open"  # From remote
        assert baseline.assignee == "jane@example.com"  # From remote
        assert baseline.headline == "Remote description"

    def test_get_remote_baseline_no_remote_state(self, temp_dir_context):
        """Test when sync_metadata exists but no remote_state."""
        retriever, mock_persistence, mock_parser, issues_dir = self._make_retriever(
            temp_dir_context=temp_dir_context
        )

        issue = Issue(
            id="issue1",
            title="Test Issue",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
        )

        issue_file = issues_dir / "issue1.md"

        # Metadata without remote_state
        sync_metadata = {
            "last_synced": "2026-01-02T10:00:00+00:00",
        }

        IssueParser.save_issue_file(issue, issue_file, sync_metadata=sync_metadata)

        baseline = retriever.get_remote_baseline(issue_file)

        assert baseline is None

    def test_get_remote_baseline_with_datetime_parsing(self, temp_dir_context):
        """Test remote baseline with datetime field parsing."""
        retriever, mock_persistence, mock_parser, issues_dir = self._make_retriever(
            temp_dir_context=temp_dir_context
        )

        issue = Issue(
            id="issue1",
            title="Test",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            issue_type=IssueType.FEATURE,
        )

        issue_file = issues_dir / "issue1.md"

        # Remote state with datetime
        sync_metadata = {
            "last_synced": "2026-01-02T10:00:00+00:00",
            "remote_state": {
                "id": "issue1",
                "title": "Test",
                "status": "open",
                "updated_at": "2026-01-02T09:00:00+00:00",
            },
        }

        IssueParser.save_issue_file(issue, issue_file, sync_metadata=sync_metadata)

        baseline = retriever.get_remote_baseline(issue_file)

        assert baseline is not None
        assert isinstance(baseline.updated_at, datetime)


class TestBaselineComparison:
    """Test comparing local and remote baselines."""

    def _make_retriever(
        self, mock_persistence=None, mock_parser=None, temp_dir_context=None
    ):
        """Create a BaselineStateRetriever with mock dependencies."""
        if mock_persistence is None:
            mock_persistence = MagicMock(spec=PersistenceInterface)
        if mock_parser is None:
            mock_parser = MagicMock(spec=IssueParserInterface)

        with tempfile.TemporaryDirectory() as tmpdir:
            issues_dir = Path(tmpdir)
            return (
                BaselineStateRetriever(issues_dir, mock_persistence),
                mock_persistence,
                mock_parser,
                issues_dir,
            )

    def test_local_and_remote_baselines_differ(self, temp_dir_context):
        """Test detecting differences between local and remote baselines."""
        retriever, mock_persistence, mock_parser, issues_dir = self._make_retriever(
            temp_dir_context=temp_dir_context
        )

        issue = Issue(
            id="issue1",
            title="Test Issue",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
            issue_type=IssueType.BUG,
            assignee="john@example.com",
        )

        issue_file = issues_dir / "issue1.md"

        # Save with remote baseline that differs
        sync_metadata = {
            "last_synced": "2026-01-02T10:00:00+00:00",
            "remote_state": {
                "id": "issue1",
                "title": "Test Issue",
                "status": "open",  # Different from local
                "assignee": "jane@example.com",  # Different from local
            },
        }

        IssueParser.save_issue_file(issue, issue_file, sync_metadata=sync_metadata)

        # Get remote baseline
        remote_baseline = retriever.get_remote_baseline(issue_file)

        assert remote_baseline is not None
        assert remote_baseline.status == "open"
        assert remote_baseline.assignee == "jane@example.com"

        # Compare with current local
        assert issue.status.value != remote_baseline.status
        assert issue.assignee != remote_baseline.assignee
