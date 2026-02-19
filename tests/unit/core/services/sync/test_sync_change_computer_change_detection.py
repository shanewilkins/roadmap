"""High-quality tests for SyncChangeComputer with change detection validation.

Focus: Validates change computation, field difference detection, enum handling.
"""

import pytest
import structlog

from roadmap.core.domain.issue import Issue, IssueType, Priority, Status
from roadmap.core.services.sync.sync_change_computer import (
    compute_changes,
)


@pytest.fixture
def logger():
    """Create a structlog logger for tests."""
    return structlog.get_logger()


@pytest.fixture
def baseline_issue():
    """Create a baseline Issue."""
    return Issue(
        id="issue-1",
        title="Baseline Title",
        status=Status.TODO,
        priority=Priority.MEDIUM,
        issue_type=IssueType.FEATURE,
        assignee="alice@example.com",
        milestone="v1-0",
        content="Baseline content",
        labels=["baseline"],
    )


@pytest.fixture
def local_issue():
    """Create a local Issue with some changes."""
    return Issue(
        id="issue-1",
        title="Local Title",
        status=Status.IN_PROGRESS,
        priority=Priority.HIGH,
        issue_type=IssueType.FEATURE,
        assignee="bob@example.com",
        milestone="v1-0",
        content="Local content",
        labels=["local", "updated"],
    )


@pytest.fixture
def remote_issue_dict():
    """Create a remote issue dict with some changes."""
    return {
        "id": "issue-1",
        "title": "Remote Title",
        "status": "blocked",
        "priority": "critical",
        "assignee": "charlie@example.com",
        "milestone": "v2-0",
        "content": "Remote content",
        "labels": ["remote"],
    }


class TestComputeLocalChanges:
    """Test computing changes from baseline to local."""

    def test_no_changes_when_identical(self, logger, baseline_issue):
        """Test no changes detected when baseline and local identical."""
        changes = compute_changes(baseline_issue, baseline_issue, logger=logger)

        assert len(changes) == 0

    def test_status_change_detected(self, logger, baseline_issue, local_issue):
        """Test status change is detected."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        assert "status" in changes
        assert changes["status"]["from"] == "todo"
        assert changes["status"]["to"] == "in-progress"

    def test_assignee_change_detected(self, logger, baseline_issue, local_issue):
        """Test assignee change is detected."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        assert "assignee" in changes
        assert changes["assignee"]["from"] == "alice@example.com"
        assert changes["assignee"]["to"] == "bob@example.com"
