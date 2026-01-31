"""Tests for LocalChangeFilter.

Tests filtering of local changes for sync operations.
"""

from unittest.mock import Mock

import pytest

from roadmap.adapters.sync.services.local_change_filter import LocalChangeFilter
from roadmap.core.models.sync_state import IssueBaseState


class TestFilterUnchangedFromBase:
    """Test filter_unchanged_from_base method."""

    def test_filter_with_no_base_state_returns_all_issues(self):
        """Test returns all issues when no base state (first sync)."""
        issues = [
            Mock(id="ISSUE-1"),
            Mock(id="ISSUE-2"),
            Mock(id="ISSUE-3"),
        ]
        current_local = {
            "ISSUE-1": Mock(id="ISSUE-1"),
            "ISSUE-2": Mock(id="ISSUE-2"),
            "ISSUE-3": Mock(id="ISSUE-3"),
        }
        base_state_issues = {}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert result == issues

    def test_filter_with_empty_issues_returns_empty(self):
        """Test returns empty list for empty issues."""
        issues = []
        current_local = {}
        base_state_issues = {"ISSUE-1": Mock()}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert result == []

    def test_filter_removes_stale_issues_not_in_local(self):
        """Test filters out issues not in current local state."""
        issues = [
            Mock(id="ISSUE-1"),
            Mock(id="ISSUE-2"),
            Mock(id="ISSUE-3"),
        ]
        current_local = {
            "ISSUE-1": Mock(id="ISSUE-1"),
            # ISSUE-2 is missing (stale)
            "ISSUE-3": Mock(id="ISSUE-3"),
        }
        base_state_issues = {
            "ISSUE-1": Mock(),
            "ISSUE-2": Mock(),
            "ISSUE-3": Mock(),
        }

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        # ISSUE-2 should be filtered out
        assert len(result) == 2
        assert result[0].id == "ISSUE-1"
        assert result[1].id == "ISSUE-3"

    def test_filter_includes_new_issues(self):
        """Test includes new issues not in base state."""
        issues = [
            Mock(id="ISSUE-1"),
            Mock(id="ISSUE-2"),
        ]
        current_local = {
            "ISSUE-1": Mock(id="ISSUE-1"),
            "ISSUE-2": Mock(id="ISSUE-2"),
        }
        base_state_issues = {
            "ISSUE-1": Mock(),
            # ISSUE-2 is new
        }

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 2  # Both issues included

    def test_filter_detects_status_change(self):
        """Test detects changes in status field."""
        local_issue = Mock(
            id="ISSUE-1",
            status=Mock(value="closed"),
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",  # Changed
            title="Test",
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 1  # Issue included due to change

    def test_filter_detects_assignee_change(self):
        """Test detects changes in assignee field."""
        local_issue = Mock(
            id="ISSUE-1",
            status=Mock(value="open"),
            assignee="user2",  # Changed
            content="Test content",
            labels=["bug"],
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 1  # Issue included due to change

    def test_filter_detects_content_change(self):
        """Test detects changes in content field."""
        local_issue = Mock(
            id="ISSUE-1",
            status=Mock(value="open"),
            assignee="user1",
            content="Updated content",  # Changed
            labels=["bug"],
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 1  # Issue included due to change

    def test_filter_detects_labels_change(self):
        """Test detects changes in labels field."""
        local_issue = Mock(
            id="ISSUE-1",
            status=Mock(value="open"),
            assignee="user1",
            content="Test content",
            labels=["bug", "urgent"],  # Changed
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 1  # Issue included due to change

    def test_filter_excludes_unchanged_issues(self):
        """Test excludes issues with no changes."""
        local_issue = Mock(
            id="ISSUE-1",
            status=Mock(value="open"),
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 0  # Issue excluded (no changes)

    def test_filter_with_string_status(self):
        """Test handles status as string (not enum)."""
        local_issue = Mock(
            id="ISSUE-1",
            status="open",  # String, not enum
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 0  # No changes

    def test_filter_with_none_labels_and_empty_labels(self):
        """Test treats None labels same as empty list."""
        local_issue = Mock(
            id="ISSUE-1",
            status=Mock(value="open"),
            assignee="user1",
            content="Test content",
            labels=None,
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test content",
            labels=[],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        assert len(result) == 0  # No changes (None == [])

    def test_filter_handles_field_extraction_exception(self):
        """Test handles exception during field extraction."""
        local_issue = Mock(id="ISSUE-1")
        local_issue.status = None  # Will cause exception
        type(local_issue).status = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("Access error"))
        )
        local_issue.assignee = "user1"
        local_issue.content = "Test"
        local_issue.labels = []

        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test",
            labels=[],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        # Should handle exception gracefully
        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        # Should still filter based on other fields
        assert isinstance(result, list)

    @pytest.mark.parametrize(
        "status_change,assignee_change,content_change,labels_change,should_include",
        [
            (True, False, False, False, True),
            (False, True, False, False, True),
            (False, False, True, False, True),
            (False, False, False, True, True),
            (False, False, False, False, False),
            (True, True, False, False, True),
            (True, True, True, True, True),
        ],
    )
    def test_filter_with_various_change_combinations(
        self,
        status_change,
        assignee_change,
        content_change,
        labels_change,
        should_include,
    ):
        """Test filter with various combinations of field changes."""
        local_issue = Mock(
            id="ISSUE-1",
            status=Mock(value="closed" if status_change else "open"),
            assignee="user2" if assignee_change else "user1",
            content="Updated" if content_change else "Test content",
            labels=["bug", "urgent"] if labels_change else ["bug"],
        )
        base_issue = IssueBaseState(
            id="ISSUE-1",
            status="open",
            title="Test",
            assignee="user1",
            content="Test content",
            labels=["bug"],
        )

        issues = [Mock(id="ISSUE-1")]
        current_local = {"ISSUE-1": local_issue}
        base_state_issues = {"ISSUE-1": base_issue}

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, current_local, base_state_issues
        )

        if should_include:
            assert len(result) == 1
        else:
            assert len(result) == 0

    def test_filter_with_multiple_issues_mixed_changes(self):
        """Test filter with multiple issues with mixed changes."""
        issues = [Mock(id=f"ISSUE-{i}") for i in range(1, 6)]

        local_issues = {
            "ISSUE-1": Mock(
                id="ISSUE-1",
                status=Mock(value="closed"),  # Changed
                assignee="user1",
                content="Test",
                labels=[],
            ),
            "ISSUE-2": Mock(
                id="ISSUE-2",
                status=Mock(value="open"),  # Unchanged
                assignee="user1",
                content="Test",
                labels=[],
            ),
            "ISSUE-3": Mock(
                id="ISSUE-3",
                status=Mock(value="open"),  # New issue
                assignee="user1",
                content="Test",
                labels=[],
            ),
            "ISSUE-4": Mock(
                id="ISSUE-4",
                status=Mock(value="open"),  # Unchanged
                assignee="user1",
                content="Test",
                labels=[],
            ),
            "ISSUE-5": Mock(
                id="ISSUE-5",
                status=Mock(value="open"),  # Changed
                assignee="user2",
                content="Test",
                labels=[],
            ),
        }

        base_issues = {
            "ISSUE-1": IssueBaseState(
                id="ISSUE-1",
                status="open",
                title="Test",
                assignee="user1",
                content="Test",
                labels=[],
            ),
            "ISSUE-2": IssueBaseState(
                id="ISSUE-2",
                status="open",
                title="Test",
                assignee="user1",
                content="Test",
                labels=[],
            ),
            # ISSUE-3 is new (not in base)
            "ISSUE-4": IssueBaseState(
                id="ISSUE-4",
                status="open",
                title="Test",
                assignee="user1",
                content="Test",
                labels=[],
            ),
            "ISSUE-5": IssueBaseState(
                id="ISSUE-5",
                status="open",
                title="Test",
                assignee="user1",
                content="Test",
                labels=[],
            ),
        }

        result = LocalChangeFilter.filter_unchanged_from_base(
            issues, local_issues, base_issues
        )

        # Should include: ISSUE-1 (status changed), ISSUE-3 (new), ISSUE-5 (assignee changed)
        assert len(result) == 3
        result_ids = {issue.id for issue in result}
        assert result_ids == {"ISSUE-1", "ISSUE-3", "ISSUE-5"}
