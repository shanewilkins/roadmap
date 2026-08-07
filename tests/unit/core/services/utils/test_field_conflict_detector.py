"""Tests for field-level conflict detection between local and remote issues.

Uses factories to create test data and parametrization for conflict scenarios.
"""

from unittest.mock import Mock

import pytest

from roadmap.core.domain.issue import Issue
from roadmap.core.services.utils.field_conflict_detector import FieldConflictDetector


@pytest.fixture
def issue_factory():
    """Factory for creating test Issue objects."""

    def _create_issue(
        issue_id: str = "issue-1",
        title: str = "Test Issue",
        status: str = "open",
        priority: str = "medium",
        content: str = "Issue content",
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> Issue:
        issue = Mock(spec=Issue)
        issue.id = issue_id
        issue.title = title
        issue.status = status
        issue.priority = priority
        issue.content = content
        issue.labels = labels or []
        issue.assignee = assignee
        issue.updated = "2026-01-29T00:00:00Z"
        return issue

    return _create_issue


@pytest.fixture
def remote_issue_factory():
    """Factory for creating test remote issue dicts."""

    def _create_remote_issue(
        issue_id: str = "remote-1",
        title: str = "Remote Issue",
        status: str = "closed",
        priority: str = "high",
        content: str = "Remote content",
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> dict:
        return {
            "id": issue_id,
            "title": title,
            "status": status,
            "priority": priority,
            "content": content,
            "labels": labels or [],
            "assignee": assignee,
            "updated_at": "2026-01-29T00:00:00Z",
        }

    return _create_remote_issue


class TestFieldConflictDetector:
    """Tests for FieldConflictDetector."""

    def test_initialization_with_default_fields(self):
        """Test detector initializes with default fields."""
        detector = FieldConflictDetector()

        assert detector.fields_to_sync == [
            "status",
            "priority",
            "content",
            "labels",
            "assignee",
        ]

    def test_initialization_with_custom_fields(self):
        """Test detector initializes with custom fields."""
        custom_fields = ["title", "status"]
        detector = FieldConflictDetector(fields_to_sync=custom_fields)

        assert detector.fields_to_sync == custom_fields

    @pytest.mark.parametrize(
        "local_status,remote_status,should_conflict",
        [
            ("open", "closed", True),
            ("open", "open", False),
            ("closed", "closed", False),
        ],
    )
    def test_detect_status_conflicts_parametrized(
        self,
        issue_factory,
        remote_issue_factory,
        local_status,
        remote_status,
        should_conflict,
    ):
        """Parametrized test for status conflicts."""
        detector = FieldConflictDetector(fields_to_sync=["status"])

        local_issue = issue_factory(status=local_status)
        remote_issue = remote_issue_factory(status=remote_status)

        conflicts = detector.detect_field_conflicts(local_issue, remote_issue)

        if should_conflict:
            assert len(conflicts) == 1
            assert conflicts[0].field_name == "status"
        else:
            assert len(conflicts) == 0

    @pytest.mark.parametrize(
        "local_priority,remote_priority,should_conflict",
        [
            ("high", "low", True),
            ("medium", "medium", False),
            ("low", "high", True),
        ],
    )
    def test_detect_priority_conflicts_parametrized(
        self,
        issue_factory,
        remote_issue_factory,
        local_priority,
        remote_priority,
        should_conflict,
    ):
        """Parametrized test for priority conflicts."""
        detector = FieldConflictDetector(fields_to_sync=["priority"])

        local_issue = issue_factory(priority=local_priority)
        remote_issue = remote_issue_factory(priority=remote_priority)

        conflicts = detector.detect_field_conflicts(local_issue, remote_issue)

        if should_conflict:
            assert len(conflicts) == 1
            assert conflicts[0].field_name == "priority"
        else:
            assert len(conflicts) == 0

    def test_detect_multiple_field_conflicts(self, issue_factory, remote_issue_factory):
        """Test detecting conflicts in multiple fields."""
        detector = FieldConflictDetector(
            fields_to_sync=["status", "priority", "assignee"]
        )

        local_issue = issue_factory(status="open", priority="medium", assignee="alice")
        remote_issue = remote_issue_factory(
            status="closed", priority="high", assignee="bob"
        )

        conflicts = detector.detect_field_conflicts(local_issue, remote_issue)

        assert len(conflicts) == 3
        field_names = {c.field_name for c in conflicts}
        assert field_names == {"status", "priority", "assignee"}

    def test_detect_no_conflicts_when_all_match(
        self, issue_factory, remote_issue_factory
    ):
        """Test that no conflicts are detected when all fields match."""
        detector = FieldConflictDetector(
            fields_to_sync=["status", "priority", "content"]
        )

        local_issue = issue_factory(
            status="open", priority="medium", content="same content"
        )
        remote_issue = remote_issue_factory(
            status="open", priority="medium", content="same content"
        )

        conflicts = detector.detect_field_conflicts(local_issue, remote_issue)

        assert len(conflicts) == 0

    def test_get_field_value_from_dict(self):
        """Test extracting field values from dict objects."""
        detector = FieldConflictDetector()
        remote_dict = {
            "title": "Dict Issue",
            "status": "open",
            "labels": ["bug", "urgent"],
        }

        title = detector._get_field_value(remote_dict, "title")
        status = detector._get_field_value(remote_dict, "status")
        labels = detector._get_field_value(remote_dict, "labels")

        assert title == "Dict Issue"
        assert status == "open"
        assert labels == ["bug", "urgent"]

    def test_get_field_value_from_object(self, issue_factory):
        """Test extracting field values from object attributes."""
        detector = FieldConflictDetector()
        issue = issue_factory(title="Object Issue", status="closed")

        title = detector._get_field_value(issue, "title")
        status = detector._get_field_value(issue, "status")

        assert title == "Object Issue"
        assert status == "closed"

    def test_get_field_value_missing_field_returns_none(self):
        """Test that missing fields return None."""
        detector = FieldConflictDetector()
        remote_dict = {"title": "Issue"}

        value = detector._get_field_value(remote_dict, "nonexistent_field")

        assert value is None

    def test_get_field_value_with_none_object(self):
        """Test that None object returns None."""
        detector = FieldConflictDetector()

        value = detector._get_field_value(None, "any_field")

        assert value is None

    def test_get_field_value_normalizes_labels_list(self, issue_factory):
        """Test that labels are sorted consistently."""
        detector = FieldConflictDetector()
        issue = issue_factory(labels=["zebra", "alpha", "beta"])

        labels = detector._get_field_value(issue, "labels")

        assert labels == ["alpha", "beta", "zebra"]

    def test_detect_labels_conflict(self, issue_factory, remote_issue_factory):
        """Test detecting conflicts in labels field."""
        detector = FieldConflictDetector(fields_to_sync=["labels"])

        local_issue = issue_factory(labels=["bug", "urgent"])
        remote_issue = remote_issue_factory(labels=["bug", "urgent", "critical"])

        conflicts = detector.detect_field_conflicts(local_issue, remote_issue)

        assert len(conflicts) == 1
        assert conflicts[0].field_name == "labels"

    def test_conflict_field_contains_both_values(
        self, issue_factory, remote_issue_factory
    ):
        """Test that ConflictField contains both local and remote values."""
        detector = FieldConflictDetector(fields_to_sync=["status"])

        local_issue = issue_factory(status="open")
        remote_issue = remote_issue_factory(status="closed")

        conflicts = detector.detect_field_conflicts(local_issue, remote_issue)

        assert conflicts[0].local_value == "open"
        assert conflicts[0].remote_value == "closed"
