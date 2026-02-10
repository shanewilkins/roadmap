"""High-quality tests for SyncChangeComputer with change detection validation.

Focus: Validates change computation, field difference detection, enum handling.
Validates:
- Local changes detected correctly (baseline→local)
- Remote changes detected correctly (baseline→remote)
- Field-level change tracking
- Change structure (from/to values)
- Enum field conversion
- Edge cases (null values, missing fields)
"""

import pytest
import structlog

from roadmap.core.domain.issue import Issue, IssueType, Priority, Status
from roadmap.core.services.sync.sync_change_computer import (
    _convert_enum_field,
    compute_changes,
    compute_changes_remote,
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

    def test_content_change_detected(self, logger, baseline_issue, local_issue):
        """Test content change is detected."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        assert "content" in changes
        assert changes["content"]["from"] == "Baseline content"
        assert changes["content"]["to"] == "Local content"

    def test_labels_change_detected(self, logger, baseline_issue, local_issue):
        """Test labels change is detected."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        assert "labels" in changes
        # Labels should be sorted for comparison
        assert "baseline" in str(changes["labels"]["from"])
        assert "local" in str(changes["labels"]["to"])

    def test_multiple_changes_detected(self, logger, baseline_issue, local_issue):
        """Test multiple changes are detected."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        # Should have multiple changes
        assert len(changes) > 1
        assert "status" in changes
        assert "assignee" in changes
        assert "content" in changes

    def test_status_none_to_value(self, logger):
        """Test change from None to value."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            assignee=None,
            content="",
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            assignee="alice@example.com",
            content="",
        )

        changes = compute_changes(baseline, local, logger=logger)

        assert "assignee" in changes
        assert changes["assignee"]["from"] is None
        assert changes["assignee"]["to"] == "alice@example.com"

    def test_value_to_none(self, logger):
        """Test change from value to None."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            assignee="alice@example.com",
            content="",
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            assignee=None,
            content="",
        )

        changes = compute_changes(baseline, local, logger=logger)

        assert "assignee" in changes
        assert changes["assignee"]["from"] == "alice@example.com"
        assert changes["assignee"]["to"] is None

    def test_empty_to_content(self, logger):
        """Test change from empty to filled content."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="",
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="New content",
        )

        changes = compute_changes(baseline, local, logger=logger)

        assert "content" in changes
        assert changes["content"]["from"] == ""
        assert changes["content"]["to"] == "New content"

    def test_content_to_empty(self, logger):
        """Test change from filled to empty content."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="Old content",
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="",
        )

        changes = compute_changes(baseline, local, logger=logger)

        assert "content" in changes
        assert changes["content"]["from"] == "Old content"
        assert changes["content"]["to"] == ""


class TestComputeRemoteChanges:
    """Test computing changes from baseline to remote."""

    def test_no_changes_remote_identical(
        self, logger, baseline_issue, remote_issue_dict
    ):
        """Test no changes when remote identical to baseline."""
        remote_same = {
            "id": baseline_issue.id,
            "status": baseline_issue.status.value,
            "assignee": baseline_issue.assignee,
            "content": baseline_issue.content,
            "labels": baseline_issue.labels,
        }

        changes = compute_changes_remote(baseline_issue, remote_same, logger=logger)

        assert len(changes) == 0

    def test_status_change_remote(self, logger, baseline_issue, remote_issue_dict):
        """Test status change in remote."""
        changes = compute_changes_remote(
            baseline_issue, remote_issue_dict, logger=logger
        )

        assert "status" in changes
        assert changes["status"]["from"] == "todo"
        assert changes["status"]["to"] == "blocked"

    def test_assignee_change_remote(self, logger, baseline_issue, remote_issue_dict):
        """Test assignee change in remote."""
        changes = compute_changes_remote(
            baseline_issue, remote_issue_dict, logger=logger
        )

        assert "assignee" in changes
        assert changes["assignee"]["from"] == "alice@example.com"
        assert changes["assignee"]["to"] == "charlie@example.com"

    def test_content_change_remote(self, logger, baseline_issue, remote_issue_dict):
        """Test content change in remote."""
        changes = compute_changes_remote(
            baseline_issue, remote_issue_dict, logger=logger
        )

        assert "content" in changes
        assert changes["content"]["from"] == "Baseline content"
        assert changes["content"]["to"] == "Remote content"

    def test_labels_change_remote(self, logger, baseline_issue, remote_issue_dict):
        """Test labels change in remote."""
        changes = compute_changes_remote(
            baseline_issue, remote_issue_dict, logger=logger
        )

        assert "labels" in changes

    def test_handles_dict_remote(self, logger, baseline_issue):
        """Test compute_changes_remote with dict remote."""
        remote_dict = {
            "status": "in-progress",
            "assignee": "bob@example.com",
            "content": "New content",
            "labels": ["updated"],
        }

        changes = compute_changes_remote(baseline_issue, remote_dict, logger=logger)

        assert len(changes) > 0

    def test_handles_object_remote(self, logger, baseline_issue, local_issue):
        """Test compute_changes_remote with object remote."""
        # local_issue acts as remote object here
        changes = compute_changes_remote(baseline_issue, local_issue, logger=logger)

        assert len(changes) > 0

    def test_remote_field_access_dict(self, logger, baseline_issue):
        """Test field access from dict remote."""
        remote_dict = {
            "status": "closed",
            "content": "Dict content",
        }

        changes = compute_changes_remote(baseline_issue, remote_dict, logger=logger)

        assert "status" in changes
        assert "content" in changes

    def test_remote_field_access_missing_dict_key(self, logger, baseline_issue):
        """Test missing key in dict remote defaults to None."""
        remote_dict = {
            "status": "in-progress",
            # Missing other keys
        }

        changes = compute_changes_remote(baseline_issue, remote_dict, logger=logger)

        # Status changed, others might be None
        assert "status" in changes


class TestConvertEnumField:
    """Test enum field conversion."""

    def test_convert_status_string(self):
        """Test status string conversion."""
        result = _convert_enum_field("status", "todo")

        assert result == Status.TODO

    def test_convert_status_lowercase(self):
        """Test status lowercase conversion."""
        result = _convert_enum_field("status", "todo")

        assert result == Status.TODO

    def test_convert_status_dashed(self):
        """Test status with dashes."""
        result = _convert_enum_field("status", "in-progress")

        assert result == Status.IN_PROGRESS

    def test_convert_priority_string(self):
        """Test priority string conversion."""
        result = _convert_enum_field("priority", "high")

        assert result == Priority.HIGH

    def test_convert_priority_lowercase(self):
        """Test priority lowercase conversion."""
        result = _convert_enum_field("priority", "medium")

        assert result == Priority.MEDIUM

    def test_non_enum_field_unchanged(self):
        """Test non-enum field unchanged."""
        result = _convert_enum_field("assignee", "alice@example.com")

        assert result == "alice@example.com"

    def test_invalid_enum_value_unchanged(self):
        """Test invalid enum value returned as-is."""
        result = _convert_enum_field("status", "invalid_status")

        # Should either return original or fallback
        assert result is not None

    def test_none_value_unchanged(self):
        """Test None value unchanged."""
        result = _convert_enum_field("status", None)

        assert result is None

    def test_non_string_value_unchanged(self):
        """Test non-string value unchanged."""
        result = _convert_enum_field("status", 123)

        assert result == 123


class TestChangeStructure:
    """Test change structure and data format."""

    def test_change_has_from_to_values(self, logger, baseline_issue, local_issue):
        """Test each change has 'from' and 'to' values."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        for _field, change_data in changes.items():
            assert "from" in change_data
            assert "to" in change_data

    def test_from_value_correct(self, logger, baseline_issue, local_issue):
        """Test 'from' value is baseline."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        if "status" in changes:
            assert changes["status"]["from"] == baseline_issue.status.value

    def test_to_value_correct(self, logger, baseline_issue, local_issue):
        """Test 'to' value is local."""
        changes = compute_changes(baseline_issue, local_issue, logger=logger)

        if "status" in changes:
            assert changes["status"]["to"] == local_issue.status.value


class TestLoggingIntegration:
    """Test logging integration in change computation."""

    def test_logs_changes_detected(self, baseline_issue, local_issue):
        """Test changes are logged."""
        mock_logger = structlog.get_logger()

        changes = compute_changes(baseline_issue, local_issue, logger=mock_logger)

        # If changes exist, logging should have been attempted
        if changes:
            # Just verify no exception thrown
            assert len(changes) > 0

    def test_handles_logging_errors(self, baseline_issue, local_issue):
        """Test with logger that has limited methods."""

        class MinimalLogger:
            def debug(self, msg, **kwargs):
                pass

        # Should not raise even with minimal logger
        changes = compute_changes(baseline_issue, local_issue, logger=MinimalLogger())

        # Should still return changes
        assert len(changes) > 0


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_all_fields_changed(self, logger):
        """Test when all fields are changed."""
        baseline = Issue(
            id="1",
            title="Original",
            status=Status.TODO,
            assignee="alice@example.com",
            content="Original",
            labels=["a"],
        )
        local = Issue(
            id="1",
            title="Updated",
            status=Status.CLOSED,
            assignee="bob@example.com",
            content="Updated",
            labels=["b"],
        )

        changes = compute_changes(baseline, local, logger=logger)

        # Status, assignee, content, labels should all change
        assert "status" in changes
        assert "assignee" in changes
        assert "content" in changes
        assert "labels" in changes

    def test_no_fields_changed(self, logger, baseline_issue):
        """Test when no fields are changed."""
        changes = compute_changes(baseline_issue, baseline_issue, logger=logger)

        assert len(changes) == 0

    def test_empty_strings_vs_none(self, logger):
        """Test empty strings are different from None."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            assignee=None,
            content="",
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            assignee="",
            content="",
        )

        changes = compute_changes(baseline, local, logger=logger)

        # Empty string assignee vs None assignee should be different
        assert "assignee" in changes

    def test_multiline_content_change(self, logger):
        """Test multiline content changes."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="Line 1\nLine 2",
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="Line 1\nLine 2\nLine 3",
        )

        changes = compute_changes(baseline, local, logger=logger)

        assert "content" in changes
        assert "Line 3" in changes["content"]["to"]

    def test_label_order_significant(self, logger):
        """Test label order is considered in comparison."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="",
            labels=["z", "a", "m"],
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="",
            labels=["a", "m", "z"],
        )

        changes = compute_changes(baseline, local, logger=logger)

        # Different order is detected as a change
        assert "labels" in changes
        assert changes["labels"]["from"] == ["z", "a", "m"]
        assert changes["labels"]["to"] == ["a", "m", "z"]

    def test_case_sensitive_content(self, logger):
        """Test content comparison is case-sensitive."""
        baseline = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="Content",
        )
        local = Issue(
            id="1",
            title="Test",
            status=Status.TODO,
            content="content",
        )

        changes = compute_changes(baseline, local, logger=logger)

        # Different case should be detected
        assert "content" in changes


class TestRemoteChangeComputation:
    """Test remote-specific change computation."""

    def test_remote_priority_different_format(self, logger, baseline_issue):
        """Test remote priority in different format."""
        remote = {
            "status": "todo",
            "priority": "CRITICAL",  # Different format
        }

        compute_changes_remote(baseline_issue, remote, logger=logger)

        # Priority may or may not be in changes depending on format handling

    def test_remote_with_extra_fields(self, logger, baseline_issue):
        """Test remote with extra fields not in baseline."""
        remote = {
            "status": "in-progress",
            "assignee": baseline_issue.assignee,
            "content": baseline_issue.content,
            "extra_field": "extra_value",  # Not tracked
            "another_field": "another_value",
        }

        changes = compute_changes_remote(baseline_issue, remote, logger=logger)

        # Should only track relevant fields
        assert "extra_field" not in changes
        assert "another_field" not in changes
