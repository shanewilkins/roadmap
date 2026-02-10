"""Tests for OperationFormatter class."""

from roadmap.common.formatters.text.operations import OperationFormatter


class TestOperationFormatterSuccess:
    """Test OperationFormatter.success() method."""

    def test_success_minimal(self):
        """Test success with minimal parameters."""
        result = OperationFormatter.success("✅", "Created")
        assert "✅ Created" in result

    def test_success_with_title(self):
        """Test success with entity title."""
        result = OperationFormatter.success("✅", "Updated", entity_title="My Issue")
        assert "✅ Updated issue: My Issue" in result

    def test_success_with_id(self):
        """Test success with entity ID."""
        result = OperationFormatter.success(
            "✅", "Created", entity_title="Test", entity_id="issue-123"
        )
        assert "issue-123" in result
        assert "ID:" in result

    def test_success_with_details(self):
        """Test success with additional details."""
        details = {"Status": "ready", "Priority": "high"}
        result = OperationFormatter.success(
            "✅", "Updated", entity_title="Test", details=details
        )
        assert "Status: ready" in result
        assert "Priority: high" in result

    def test_success_multiline_format(self):
        """Test that success returns properly formatted multiline string."""
        result = OperationFormatter.success(
            "✅",
            "Closed",
            entity_title="Fix bug",
            entity_id="issue-456",
            details={"Reason": "Fixed"},
        )
        lines = result.split("\n")
        assert len(lines) >= 3


class TestOperationFormatterFailure:
    """Test OperationFormatter.failure() method."""

    def test_failure_minimal(self):
        """Test failure with minimal parameters."""
        result = OperationFormatter.failure("delete")
        assert "❌ Failed to delete" in result

    def test_failure_with_entity_id(self):
        """Test failure with entity ID."""
        result = OperationFormatter.failure("update", entity_id="issue-123")
        assert "issue-123" in result

    def test_failure_with_error(self):
        """Test failure with error message."""
        result = OperationFormatter.failure(
            "close", entity_id="issue-789", error="Issue not found"
        )
        assert "Issue not found" in result
        assert "Error:" in result

    def test_failure_with_suggestion(self):
        """Test failure with recovery suggestion."""
        result = OperationFormatter.failure(
            "sync",
            error="Connection timeout",
            suggestion="Check your internet connection",
        )
        assert "Connection timeout" in result
        assert "Check your internet connection" in result
        assert "💡" in result

    def test_failure_multiline_format(self):
        """Test that failure returns properly formatted multiline string."""
        result = OperationFormatter.failure(
            "link", entity_id="issue-999", error="Not found", suggestion="Try again"
        )
        lines = result.split("\n")
        assert len(lines) >= 3


class TestOperationFormatterEntity:
    """Test OperationFormatter.entity() method."""

    def test_entity_minimal(self):
        """Test entity with minimal parameters."""
        result = OperationFormatter.entity("issue-123")
        assert "issue-123" in result
        assert "ID:" in result

    def test_entity_with_title(self):
        """Test entity with title."""
        result = OperationFormatter.entity(
            "issue-123", entity_title="My Feature", entity_type="issue"
        )
        assert "My Feature" in result
        assert "Issue:" in result

    def test_entity_with_status(self):
        """Test entity with status."""
        result = OperationFormatter.entity(
            "issue-456", entity_title="Bug Fix", status="closed"
        )
        assert "closed" in result
        assert "Status:" in result

    def test_entity_with_details(self):
        """Test entity with additional details."""
        details = {"Assignee": "Alice", "Milestone": "v1-0"}
        result = OperationFormatter.entity(
            "issue-789", entity_title="Enhancement", details=details
        )
        assert "Assignee: Alice" in result
        assert "Milestone: v1-0" in result

    def test_entity_custom_type(self):
        """Test entity with custom type."""
        result = OperationFormatter.entity(
            "milestone-1", entity_title="Release 2.0", entity_type="milestone"
        )
        assert "Milestone:" in result

    def test_entity_multiline_format(self):
        """Test that entity returns properly formatted multiline string."""
        result = OperationFormatter.entity(
            "issue-111",
            entity_title="Complex task",
            entity_type="issue",
            status="in_progress",
            details={"Owner": "Bob", "Due": "2025-01-01"},
        )
        lines = result.split("\n")
        assert len(lines) >= 4


class TestOperationFormatterIntegration:
    """Integration tests for OperationFormatter."""

    def test_success_and_failure_consistency(self):
        """Test that success and failure formats are consistent."""
        success = OperationFormatter.success(
            "✅", "Created", entity_title="Test", entity_id="test-123"
        )
        failure = OperationFormatter.failure(
            "create", entity_id="test-123", error="Failed"
        )

        # Both should contain ID
        assert "test-123" in success
        assert "test-123" in failure

        # Should be multiline when has enough content
        assert "\n" in success
        assert "\n" in failure

    def test_entity_formatting_consistency(self):
        """Test that entity formatting is consistent with success/failure."""
        entity = OperationFormatter.entity("issue-1", entity_title="Test Task")
        success = OperationFormatter.success("✅", "Created", entity_title="Test Task")

        # Both should contain title
        assert "Test Task" in entity
        assert "Test Task" in success

    def test_empty_values_handling(self):
        """Test that None/empty values are handled gracefully."""
        result1 = OperationFormatter.success("✅", "Done", entity_title=None)
        result2 = OperationFormatter.failure("delete", entity_id=None)
        result3 = OperationFormatter.entity("id-1", details=None, status=None)

        # Should not contain "None" strings
        assert "None" not in result1
        assert "None" not in result2
        assert "None" not in result3

    def test_special_characters_in_content(self):
        """Test handling of special characters in formatted content."""
        result = OperationFormatter.success(
            "✅", "Fixed", entity_title="Fix [critical] bug"
        )
        assert "Fix [critical] bug" in result

    def test_long_content_handling(self):
        """Test handling of very long content."""
        long_title = "A" * 500
        result = OperationFormatter.success("✅", "Created", entity_title=long_title)
        assert long_title in result
