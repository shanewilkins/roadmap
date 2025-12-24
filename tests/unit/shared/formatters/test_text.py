"""Unit tests for text formatting utilities."""

from roadmap.shared.formatters.text import (
    _format_table_simple,
    format_header,
    format_panel,
    format_table,
)


class TestFormatTable:
    """Test format_table function."""

    def test_format_table_basic(self):
        """Test basic table formatting."""
        columns = ["Name", "Age"]
        rows = [("Alice", 30), ("Bob", 25)]
        result = format_table("People", columns, rows)
        assert result is not None

    def test_format_table_empty_rows(self):
        """Test table formatting with empty rows."""
        columns = ["Name", "Age"]
        rows = []
        result = format_table("Empty", columns, rows)
        assert result is not None

    def test_format_table_multiple_rows(self):
        """Test table with multiple rows."""
        columns = ["ID", "Status", "Title"]
        rows = [
            (1, "open", "First issue"),
            (2, "closed", "Second issue"),
            (3, "in-progress", "Third issue"),
        ]
        result = format_table("Issues", columns, rows)
        assert result is not None

    def test_format_table_with_numbers(self):
        """Test table with numeric values."""
        columns = ["Item", "Count", "Percentage"]
        rows = [(("Completed", 45, 90.5), ("Pending", 5, 9.5))]
        result = format_table("Stats", columns, rows)
        assert result is not None

    def test_format_table_simple_fallback(self):
        """Test simple table formatting fallback."""
        columns = ["A", "B"]
        rows = [("1", "2"), ("3", "4")]
        result = _format_table_simple("Test", columns, rows)
        assert "Test" in result
        assert "A" in result

    def test_format_table_with_long_content(self):
        """Test table with long content."""
        columns = ["Short", "Long"]
        rows = [("a", "b" * 50)]
        result = format_table("Long", columns, rows)
        assert result is not None


class TestFormatPanel:
    """Test format_panel function."""

    def test_format_panel_basic(self):
        """Test basic panel formatting."""
        panel = format_panel("Test content")
        assert panel is not None

    def test_format_panel_with_title(self):
        """Test panel with title."""
        panel = format_panel("Content", title="My Title")
        assert panel is not None

    def test_format_panel_expanded(self):
        """Test expanded panel."""
        panel = format_panel("Content", title="Title", expand=True)
        assert panel is not None
        assert panel.expand

    def test_format_panel_not_expanded(self):
        """Test non-expanded panel."""
        panel = format_panel("Content", expand=False)
        assert panel is not None
        assert not panel.expand

    def test_format_panel_empty_content(self):
        """Test panel with empty content."""
        panel = format_panel("")
        assert panel is not None


class TestFormatHeader:
    """Test format_header function."""

    def test_format_header_level_1(self):
        """Test level 1 header formatting."""
        header = format_header("Title", level=1)
        assert header is not None
        assert header.style is not None

    def test_format_header_level_2(self):
        """Test level 2 header formatting."""
        header = format_header("Subtitle", level=2)
        assert header is not None
        assert header.style is not None

    def test_format_header_level_3(self):
        """Test level 3 header formatting."""
        header = format_header("Small", level=3)
        assert header is not None
        assert header.style is not None

    def test_format_header_default_level(self):
        """Test header with default level."""
        header = format_header("Default")
        assert header is not None

    def test_format_header_empty_text(self):
        """Test header with empty text."""
        header = format_header("")
        assert header is not None

    def test_format_header_special_characters(self):
        """Test header with special characters."""
        header = format_header("Title: Special (123) [Test]")
        assert header is not None


class TestFormatterIntegration:
    """Integration tests for text formatters."""

    def test_combine_table_and_panel(self):
        """Test combining table and panel formatting."""
        table = format_table("Data", ["Col1", "Col2"], [("A", "B")])
        panel = format_panel(table, title="Wrapped")
        assert panel is not None

    def test_multiple_headers(self):
        """Test creating multiple headers in sequence."""
        h1 = format_header("Main", level=1)
        h2 = format_header("Section", level=2)
        h3 = format_header("Item", level=3)
        assert h1 is not None
        assert h2 is not None
        assert h3 is not None

    def test_format_with_unicode(self):
        """Test formatting with unicode characters."""
        columns = ["Name", "Status"]
        rows = [("Test ✓", "Done ✓"), ("Test ✗", "Failed ✗")]
        result = format_table("Unicode", columns, rows)
        assert result is not None
