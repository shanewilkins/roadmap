"""Tests for display formatting utilities."""

from roadmap.common.formatters.text.display import (
    format_display_list,
    format_display_pairs,
)


class TestFormatDisplayList:
    """Test format_display_list function."""

    def test_format_display_list_empty(self):
        """Test formatting empty list."""
        result = format_display_list([])
        assert result == ""

    def test_format_display_list_single_item(self):
        """Test formatting single item."""
        result = format_display_list(["Item 1"])
        assert "• Item 1" in result

    def test_format_display_list_multiple_items(self):
        """Test formatting multiple items."""
        items = ["Item 1", "Item 2", "Item 3"]
        result = format_display_list(items)
        assert "• Item 1" in result
        assert "• Item 2" in result
        assert "• Item 3" in result

    def test_format_display_list_with_title(self):
        """Test formatting list with title."""
        result = format_display_list(["Item 1"], title="My List")
        assert "[bold]My List[/bold]" in result
        assert "• Item 1" in result

    def test_format_display_list_preserves_order(self):
        """Test that items are in correct order."""
        items = ["First", "Second", "Third"]
        result = format_display_list(items)
        lines = result.split("\n")
        assert "First" in lines[0]
        assert "Second" in lines[1]
        assert "Third" in lines[2]

    def test_format_display_list_with_special_characters(self):
        """Test formatting items with special characters."""
        items = ["Item with @mention", "Item with #tag", "Item with $symbol"]
        result = format_display_list(items)
        assert "Item with @mention" in result
        assert "Item with #tag" in result
        assert "Item with $symbol" in result


class TestFormatDisplayPairs:
    """Test format_display_pairs function."""

    def test_format_display_pairs_empty(self):
        """Test formatting empty dictionary."""
        result = format_display_pairs({})
        assert result == ""

    def test_format_display_pairs_single_pair(self):
        """Test formatting single key-value pair."""
        result = format_display_pairs({"key": "value"})
        assert "key" in result
        assert "value" in result
        assert ":" in result

    def test_format_display_pairs_multiple_pairs(self):
        """Test formatting multiple pairs."""
        pairs = {"name": "John", "age": "30", "city": "NYC"}
        result = format_display_pairs(pairs)
        assert "name" in result
        assert "John" in result
        assert "age" in result
        assert "30" in result
        assert "city" in result
        assert "NYC" in result

    def test_format_display_pairs_with_title(self):
        """Test formatting pairs with title."""
        result = format_display_pairs({"key": "value"}, title="Info")
        assert "[bold]Info[/bold]" in result
        assert "key" in result

    def test_format_display_pairs_alignment(self):
        """Test that keys are right-aligned."""
        pairs = {"short": "value1", "very_long_key": "value2"}
        result = format_display_pairs(pairs)
        lines = result.split("\n")
        # Both lines should have same column for values (alignment)
        # Find position of ':' in each line
        colons = [line.index(":") for line in lines if ":" in line]
        assert len(set(colons)) == 1, "Values should be aligned"

    def test_format_display_pairs_with_numeric_values(self):
        """Test formatting with numeric values."""
        pairs = {"count": 42, "ratio": 3.14, "enabled": True}
        result = format_display_pairs(pairs)
        assert "42" in result
        assert "3.14" in result
        assert "True" in result

    def test_format_display_pairs_with_none_values(self):
        """Test formatting with None values."""
        pairs = {"present": "value", "absent": None}
        result = format_display_pairs(pairs)
        assert "present" in result
        assert "value" in result
        assert "absent" in result
        assert "None" in result
