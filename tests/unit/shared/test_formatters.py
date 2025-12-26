"""Unit tests for formatters module."""

import pytest

from roadmap.shared.formatters.text.basic import (
    _format_table_simple,
    format_header,
    format_panel,
    format_table,
)


class TestFormatTable:
    """Test format_table function."""

    @pytest.mark.parametrize(
        "title,columns,rows,description",
        [
            (
                "People",
                ["Name", "Age"],
                [("Alice", 30), ("Bob", 25)],
                "basic",
            ),
            (
                "Empty",
                ["Name", "Age"],
                [],
                "empty_rows",
            ),
            (
                "Issues",
                ["ID", "Status", "Title"],
                [
                    (1, "open", "First issue"),
                    (2, "closed", "Second issue"),
                    (3, "in-progress", "Third issue"),
                ],
                "multiple_rows",
            ),
            (
                "Stats",
                ["Item", "Count", "Percentage"],
                [(("Completed", 45, 90.5), ("Pending", 5, 9.5))],
                "with_numbers",
            ),
            (
                "Long",
                ["Short", "Long"],
                [("a", "b" * 50)],
                "with_long_content",
            ),
        ],
    )
    def test_format_table(self, title, columns, rows, description):
        """Test table formatting with various configurations."""
        result = format_table(title, columns, rows)
        assert result is not None

    def test_format_table_simple_fallback(self):
        """Test simple table formatting fallback."""
        columns = ["A", "B"]
        rows = [("1", "2"), ("3", "4")]
        result = _format_table_simple("Test", columns, rows)
        assert "Test" in result
        assert "A" in result


class TestFormatPanel:
    """Test format_panel function."""

    @pytest.mark.parametrize(
        "content,title,expand,description",
        [
            ("Test content", None, None, "basic"),
            ("Content", "My Title", None, "with_title"),
            ("Content", "Title", True, "expanded"),
            ("Content", None, False, "not_expanded"),
            ("", None, None, "empty_content"),
        ],
    )
    def test_format_panel(self, content, title, expand, description):
        """Test panel formatting with various configurations."""
        if expand is None:
            panel = format_panel(content, title=title)
        else:
            panel = format_panel(content, title=title, expand=expand)
        assert panel is not None
        if expand is not None:
            assert panel.expand == expand


class TestFormatHeader:
    """Test format_header function."""

    @pytest.mark.parametrize(
        "text,level,description",
        [
            ("Title", 1, "level_1"),
            ("Subtitle", 2, "level_2"),
            ("Small", 3, "level_3"),
            ("Default", None, "default_level"),
            ("", None, "empty_text"),
            ("Title: Special (123) [Test]", None, "special_characters"),
        ],
    )
    def test_format_header(self, text, level, description):
        """Test header formatting with various levels and inputs."""
        if level is None:
            header = format_header(text)
        else:
            header = format_header(text, level=level)
        assert header is not None
        assert header.style is not None or text == ""


class TestFormatterIntegration:
    """Integration tests for formatters."""

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


class TestFormatterModuleExports:
    """Test that all formatters are properly imported and exported."""

    def test_formatters_module_import(self):
        """Test that formatters module can be imported."""
        from roadmap import shared

        assert hasattr(shared, "formatters")

    def test_issue_exporter_available(self):
        """Test that IssueExporter is available in formatters."""
        from roadmap.shared.formatters.export.issue_exporter import IssueExporter

        assert IssueExporter is not None

    def test_kanban_organizer_available(self):
        """Test that KanbanOrganizer is available in formatters."""
        from roadmap.shared.formatters.kanban import KanbanOrganizer

        assert KanbanOrganizer is not None

    def test_kanban_layout_available(self):
        """Test that KanbanLayout is available in formatters."""
        from roadmap.shared.formatters.kanban import KanbanLayout

        assert KanbanLayout is not None

    def test_table_formatters_available(self):
        """Test that table formatters are available."""
        from roadmap.shared.formatters.tables import (
            IssueTableFormatter,
            MilestoneTableFormatter,
            ProjectTableFormatter,
        )

        assert IssueTableFormatter is not None
        assert MilestoneTableFormatter is not None
        assert ProjectTableFormatter is not None
