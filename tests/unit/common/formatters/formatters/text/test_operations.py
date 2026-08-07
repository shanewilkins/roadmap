"""Tests for text operations formatter."""

from unittest.mock import Mock

import pytest

from roadmap.common.formatters.text.operations import (
    OperationFormatter,
    format_entity_details,
    format_list_items,
    format_operation_failure,
    format_operation_success,
    print_operation_failure,
    print_operation_success,
)


class TestOperationFormatter:
    """Tests for OperationFormatter class."""

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            (
                {
                    "emoji": "✅",
                    "action": "Created",
                    "entity_title": "New Feature",
                    "entity_id": "ISSUE-123",
                    "details": {"Priority": "High", "Assignee": "John"},
                },
                [
                    "✅ Created issue: New Feature",
                    "ID: ISSUE-123",
                    "Priority: High",
                    "Assignee: John",
                ],
            ),
            ({"emoji": "✅", "action": "Created"}, ["✅ Created"]),
            (
                {"emoji": "✅", "action": "Closed", "entity_title": "Bug Fix"},
                ["✅ Closed issue: Bug Fix"],
            ),
            (
                {
                    "emoji": "✅",
                    "action": "Updated",
                    "entity_id": "ISSUE-456",
                    "details": {},
                },
                ["✅ Updated", "ID: ISSUE-456"],
            ),
        ],
    )
    def test_success_various(self, kwargs, expected):
        result = OperationFormatter.success(**kwargs)
        for exp in expected:
            assert exp in result

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            (
                {
                    "action": "create",
                    "entity_id": "ISSUE-789",
                    "error": "Permission denied",
                    "suggestion": "Check your credentials",
                },
                [
                    "❌ Failed to create issue: ISSUE-789",
                    "Error: Permission denied",
                    "💡 Check your credentials",
                ],
            ),
            ({"action": "delete"}, ["❌ Failed to delete"]),
            (
                {"action": "update", "error": "Network error"},
                ["❌ Failed to update", "Error: Network error"],
            ),
        ],
    )
    def test_failure_various(self, kwargs, expected):
        result = OperationFormatter.failure(**kwargs)
        for exp in expected:
            assert exp in result
        if "suggestion" not in kwargs:
            assert "💡" not in result

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            (
                {
                    "entity_id": "ISSUE-001",
                    "entity_title": "Feature Request",
                    "entity_type": "issue",
                    "status": "Open",
                    "details": {"Priority": "Medium", "Created": "2024-01-01"},
                },
                [
                    "📋 Issue: Feature Request",
                    "ID: ISSUE-001",
                    "Status: Open",
                    "Priority: Medium",
                    "Created: 2024-01-01",
                ],
            ),
            ({"entity_id": "ISSUE-002", "entity_type": "milestone"}, ["ID: ISSUE-002"]),
            ({"entity_id": "ISSUE-003"}, ["ID: ISSUE-003"]),
            (
                {"entity_id": "ISSUE-004", "entity_title": "Test Item"},
                ["📋 Item: Test Item"],
            ),
        ],
    )
    def test_entity_various(self, kwargs, expected):
        result = OperationFormatter.entity(**kwargs)
        for exp in expected:
            assert exp in result


class TestFormatOperationSuccess:
    """Tests for format_operation_success function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = format_operation_success("✅", "Created")
        assert isinstance(result, list)

    def test_success_with_all_params(self):
        """Test with all parameters."""
        result = format_operation_success(
            emoji="✅",
            action="Created",
            entity_title="New Issue",
            entity_id="ISSUE-123",
            reason="User request",
            extra_details={"Created By": "Admin"},
        )

        assert any("✅ Created" in line for line in result)
        assert any("ID: ISSUE-123" in line for line in result)
        assert any("Reason: User request" in line for line in result)
        assert any("Created By: Admin" in line for line in result)

    def test_success_returns_multiple_lines(self):
        """Test that function returns multiple lines when needed."""
        result = format_operation_success(
            emoji="✅",
            action="Updated",
            entity_title="Test Issue",
            entity_id="ISSUE-456",
        )

        assert len(result) >= 2

    def test_success_single_line_minimal(self):
        """Test single line for minimal params."""
        result = format_operation_success("✅", "Done")
        assert len(result) == 1


class TestFormatOperationFailure:
    """Tests for format_operation_failure function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = format_operation_failure("create")
        assert isinstance(result, list)

    def test_failure_with_all_params(self):
        """Test with all parameters."""
        result = format_operation_failure(
            action="delete",
            entity_id="ISSUE-789",
            error="Not found",
            suggestion="Check the ID",
        )

        assert any("❌ Failed to delete" in line for line in result)
        assert any("Error: Not found" in line for line in result)
        assert any("💡 Check the ID" in line for line in result)

    def test_failure_single_line(self):
        """Test single line failure."""
        result = format_operation_failure("archive")
        assert len(result) == 1
        assert "❌ Failed to archive" in result[0]


class TestFormatEntityDetails:
    """Tests for format_entity_details function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = format_entity_details("ISSUE-001")
        assert isinstance(result, list)

    def test_with_all_params(self):
        """Test with all parameters."""
        result = format_entity_details(
            entity_id="ISSUE-123",
            entity_title="Test Bug",
            entity_type="issue",
            status="Open",
            details={"Assigned To": "John", "Severity": "High"},
        )

        assert any("📋 Issue: Test Bug" in line for line in result)
        assert any("ID: ISSUE-123" in line for line in result)
        assert any("Status: Open" in line for line in result)
        assert any("Assigned To: John" in line for line in result)

    def test_without_title(self):
        """Test without entity title."""
        result = format_entity_details("ISSUE-456")
        assert len(result) >= 1
        assert any("ID: ISSUE-456" in line for line in result)

    def test_custom_entity_type(self):
        """Test with custom entity type."""
        result = format_entity_details(
            entity_id="MILESTONE-1",
            entity_type="milestone",
            entity_title="v1-0",
        )

        assert any("Milestone" in line for line in result)


class TestFormatListItems:
    """Tests for format_list_items function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        result = format_list_items([])
        assert isinstance(result, list)

    def test_empty_list(self):
        """Test with empty list."""
        result = format_list_items([])
        assert result == []

    def test_single_item(self):
        """Test with single item."""
        items = [{"id": "ISSUE-001", "title": "First Issue"}]
        result = format_list_items(items)

        assert len(result) == 1
        assert "ISSUE-00" in result[0]  # ID is truncated to 8 chars
        assert "First Issue" in result[0]

    def test_multiple_items(self):
        """Test with multiple items."""
        items = [
            {"id": "ISSUE-001", "title": "First"},
            {"id": "ISSUE-002", "title": "Second"},
            {"id": "ISSUE-003", "title": "Third"},
        ]
        result = format_list_items(items)

        assert len(result) == 3

    def test_truncates_long_ids(self):
        """Test that long IDs are truncated to 8 chars."""
        items = [{"id": "ISSUE-123456789abcdef", "title": "Test"}]
        result = format_list_items(items)

        assert "ISSUE-12" in result[0]
        assert "ISSUE-123456789" not in result[0]

    def test_show_count_parameter(self):
        """Test show_count parameter limits items."""
        items = [
            {"id": "ISSUE-001", "title": "First"},
            {"id": "ISSUE-002", "title": "Second"},
            {"id": "ISSUE-003", "title": "Third"},
            {"id": "ISSUE-004", "title": "Fourth"},
        ]
        result = format_list_items(items, show_count=2)

        # Should show 2 items plus the "... and 2 more" line
        assert len(result) == 3
        assert "and 2 more" in result[-1]

    def test_show_count_no_truncation(self):
        """Test show_count when items are fewer."""
        items = [
            {"id": "ISSUE-001", "title": "First"},
            {"id": "ISSUE-002", "title": "Second"},
        ]
        result = format_list_items(items, show_count=5)

        # Should show all items, no truncation
        assert len(result) == 2

    def test_custom_more_suffix(self):
        """Test custom more_suffix parameter."""
        items = [
            {"id": "ISSUE-001", "title": "First"},
            {"id": "ISSUE-002", "title": "Second"},
            {"id": "ISSUE-003", "title": "Third"},
        ]
        result = format_list_items(
            items, show_count=1, more_suffix="+ {count} more items"
        )

        assert "+ 2 more items" in result[-1]

    def test_missing_id_field(self):
        """Test handling missing id field."""
        items = [{"title": "No ID"}]
        result = format_list_items(items)

        assert len(result) == 1

    def test_missing_title_field(self):
        """Test handling missing title field."""
        items = [{"id": "ISSUE-001"}]
        result = format_list_items(items)

        assert len(result) == 1
        assert "ISSUE-00" in result[0]  # ID is truncated to 8 chars


class TestPrintOperationSuccess:
    """Tests for print_operation_success function."""

    def test_prints_to_console(self):
        """Test that function prints to console."""
        mock_console = Mock()

        print_operation_success(
            mock_console,
            "✅",
            "Created",
            entity_title="Test",
            entity_id="ISSUE-001",
        )

        assert mock_console.print.called
        assert mock_console.print.call_count >= 1

    def test_prints_multiple_lines(self):
        """Test printing multiple lines."""
        mock_console = Mock()

        print_operation_success(
            mock_console,
            "✅",
            "Created",
            entity_title="Test",
            entity_id="ISSUE-001",
            reason="Test reason",
        )

        assert mock_console.print.call_count >= 2

    def test_single_line_print(self):
        """Test printing single line."""
        mock_console = Mock()

        print_operation_success(mock_console, "✅", "Done")

        mock_console.print.assert_called_once()


class TestPrintOperationFailure:
    """Tests for print_operation_failure function."""

    def test_prints_to_console(self):
        """Test that function prints to console."""
        mock_console = Mock()

        print_operation_failure(
            mock_console,
            "create",
            entity_id="ISSUE-001",
            error="Test error",
        )

        assert mock_console.print.called

    def test_prints_multiple_lines(self):
        """Test printing multiple lines."""
        mock_console = Mock()

        print_operation_failure(
            mock_console,
            "delete",
            entity_id="ISSUE-001",
            error="Test error",
            suggestion="Try again",
        )

        assert mock_console.print.call_count >= 2

    def test_prints_error_and_suggestion(self):
        """Test that error and suggestion are both printed."""
        mock_console = Mock()

        print_operation_failure(
            mock_console,
            "update",
            error="Network failed",
            suggestion="Check connection",
        )

        assert mock_console.print.call_count >= 2


@pytest.mark.parametrize(
    "emoji,action",
    [
        ("✅", "Created"),
        ("🚫", "Blocked"),
        ("📊", "Updated"),
        ("⏭️", "Skipped"),
    ],
)
def test_success_various_emojis(emoji, action):
    """Test success with various emojis and actions."""
    result = OperationFormatter.success(emoji, action)
    assert emoji in result
    assert action in result


@pytest.mark.parametrize(
    "action",
    [
        "create",
        "delete",
        "update",
        "archive",
        "restore",
    ],
)
def test_failure_various_actions(action):
    """Test failure with various actions."""
    result = OperationFormatter.failure(action)
    assert "❌" in result
    assert f"Failed to {action}" in result


@pytest.mark.parametrize("item_count", [0, 1, 5, 10])
def test_format_list_items_counts(item_count):
    """Test format_list_items with various counts."""
    items = [{"id": f"ISSUE-{i:03d}", "title": f"Issue {i}"} for i in range(item_count)]
    result = format_list_items(items)
    assert len(result) == item_count
