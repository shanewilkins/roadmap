"""Tests for text operations formatter."""

from unittest.mock import Mock

import pytest

from roadmap.shared.formatters.text.operations import (
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

    def test_success_with_all_params(self):
        """Test success formatting with all parameters."""
        result = OperationFormatter.success(
            emoji="✅",
            action="Created",
            entity_title="New Feature",
            entity_id="ISSUE-123",
            details={"Priority": "High", "Assignee": "John"},
        )

        assert "✅ Created issue: New Feature" in result
        assert "ID: ISSUE-123" in result
        assert "Priority: High" in result
        assert "Assignee: John" in result

    def test_success_minimal_params(self):
        """Test success formatting with minimal parameters."""
        result = OperationFormatter.success(emoji="✅", action="Created")

        assert "✅ Created" in result
        assert "\n" not in result or len(result.split("\n")) == 1

    def test_success_with_entity_title_only(self):
        """Test success with only entity title."""
        result = OperationFormatter.success(
            emoji="✅",
            action="Closed",
            entity_title="Bug Fix",
        )

        assert "✅ Closed issue: Bug Fix" in result
        assert "ID:" not in result

    def test_success_with_empty_details(self):
        """Test success with empty details dict."""
        result = OperationFormatter.success(
            emoji="✅",
            action="Updated",
            entity_id="ISSUE-456",
            details={},
        )

        assert "✅ Updated" in result
        assert "ID: ISSUE-456" in result

    def test_failure_with_all_params(self):
        """Test failure formatting with all parameters."""
        result = OperationFormatter.failure(
            action="create",
            entity_id="ISSUE-789",
            error="Permission denied",
            suggestion="Check your credentials",
        )

        assert "❌ Failed to create issue: ISSUE-789" in result
        assert "Error: Permission denied" in result
        assert "💡 Check your credentials" in result

    def test_failure_minimal_params(self):
        """Test failure formatting with minimal parameters."""
        result = OperationFormatter.failure(action="delete")

        assert "❌ Failed to delete" in result

    def test_failure_with_error_only(self):
        """Test failure with error but no suggestion."""
        result = OperationFormatter.failure(
            action="update",
            error="Network error",
        )

        assert "❌ Failed to update" in result
        assert "Error: Network error" in result
        assert "💡" not in result

    def test_entity_with_all_params(self):
        """Test entity formatting with all parameters."""
        result = OperationFormatter.entity(
            entity_id="ISSUE-001",
            entity_title="Feature Request",
            entity_type="issue",
            status="Open",
            details={"Priority": "Medium", "Created": "2024-01-01"},
        )

        assert "📋 Issue: Feature Request" in result
        assert "ID: ISSUE-001" in result
        assert "Status: Open" in result
        assert "Priority: Medium" in result
        assert "Created: 2024-01-01" in result

    def test_entity_without_title(self):
        """Test entity formatting without title."""
        result = OperationFormatter.entity(
            entity_id="ISSUE-002",
            entity_type="milestone",
        )

        assert "ID: ISSUE-002" in result

    def test_entity_minimal_params(self):
        """Test entity with minimal parameters."""
        result = OperationFormatter.entity(entity_id="ISSUE-003")

        assert "ID: ISSUE-003" in result

    def test_entity_default_type(self):
        """Test entity with default type."""
        result = OperationFormatter.entity(
            entity_id="ISSUE-004",
            entity_title="Test Item",
        )

        assert "📋 Item: Test Item" in result


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
            entity_title="v1.0",
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
