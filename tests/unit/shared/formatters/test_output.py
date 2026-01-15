"""Unit tests for output formatting utilities."""

from roadmap.common.models import ColumnDef, ColumnType, TableData
from roadmap.shared.formatters.output import (
    CSVOutputFormatter,
    JSONOutputFormatter,
    OutputFormatter,
    PlainTextOutputFormatter,
)


class TestOutputFormatter:
    """Test OutputFormatter class."""

    def create_table_data(self, rows=None):
        """Create sample TableData for testing."""
        from tests.unit.shared.test_data_factory import TestDataFactory

        if rows is None:
            rows = [
                [TestDataFactory.issue_id(), TestDataFactory.message(), "Open"],
                [TestDataFactory.issue_id(), TestDataFactory.message(), "Closed"],
            ]

        columns = [
            ColumnDef(
                name="id",
                display_name="ID",
                type=ColumnType.STRING,
                width=8,
                display_style="cyan",
            ),
            ColumnDef(
                name="title",
                display_name="Title",
                type=ColumnType.STRING,
                width=20,
                display_style="white",
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.STRING,
                width=10,
                display_style="green",
            ),
        ]

        return TableData(
            columns=columns,
            rows=rows,
            title="Test Table",
            total_count=len(rows),
            returned_count=len(rows),
        )

    def test_output_formatter_initialization(self):
        """Test OutputFormatter initialization."""
        table = self.create_table_data()
        formatter = OutputFormatter(table)
        assert formatter.table == table

    def test_to_rich_returns_table(self):
        """Test to_rich returns a Rich Table object."""
        table = self.create_table_data()
        formatter = OutputFormatter(table)
        result = formatter.to_rich()
        assert result is not None
        # Rich Table has a title attribute
        assert hasattr(result, "title")

    def test_to_json_returns_valid_json(self):
        """Test to_json returns valid JSON string."""
        import json

        table = self.create_table_data()
        formatter = OutputFormatter(table)
        result = formatter.to_json()

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "title" in parsed
        assert parsed["title"] == "Test Table"

    def test_to_csv_returns_string(self):
        """Test to_csv returns CSV string."""
        table = self.create_table_data()
        formatter = OutputFormatter(table)
        result = formatter.to_csv()

        assert isinstance(result, str)
        assert "ID" in result
        assert "Title" in result
        assert "Status" in result

    def test_to_plain_text_returns_string(self):
        """Test to_plain_text returns formatted text."""
        table = self.create_table_data()
        formatter = OutputFormatter(table)
        result = formatter.to_plain_text()

        assert isinstance(result, str)
        assert "ID" in result
        assert "Title" in result
        assert "Status" in result

    def test_to_markdown_returns_string(self):
        """Test to_markdown returns Markdown format."""
        table = self.create_table_data()
        formatter = OutputFormatter(table)
        result = formatter.to_markdown()

        assert isinstance(result, str)
        assert "##" in result  # Markdown title marker
        assert "|" in result  # Markdown table pipes

    def test_to_csv_with_empty_rows(self):
        """Test to_csv with empty rows."""
        table = self.create_table_data(rows=[])
        formatter = OutputFormatter(table)
        result = formatter.to_csv()

        assert result == ""

    def test_to_json_with_empty_rows(self):
        """Test to_json with empty rows."""
        import json

        table = self.create_table_data(rows=[])
        formatter = OutputFormatter(table)
        result = formatter.to_json()

        parsed = json.loads(result)
        assert parsed["rows"] == []

    def test_emoji_replacement_in_plain_text(self):
        """Test emoji replacement in plain text output."""
        rows = [["✅", "❌", "⚠️"]]
        table = self.create_table_data(rows=rows)
        formatter = OutputFormatter(table)
        result = formatter.to_plain_text()

        # Emoji should be replaced
        assert "[OK]" in result or "✅" not in result or "[OK]" in result

    def test_output_formatter_with_none_values(self):
        """Test OutputFormatter handles None values gracefully."""
        rows = [["ID-1", None, "Open"]]
        table = self.create_table_data(rows=rows)
        formatter = OutputFormatter(table)

        # Should not raise exceptions
        json_result = formatter.to_json()
        csv_result = formatter.to_csv()
        text_result = formatter.to_plain_text()

        assert json_result is not None
        assert csv_result is not None
        assert text_result is not None


class TestSpecializedFormatters:
    """Test specialized formatter classes."""

    def create_table_data(self):
        """Create sample TableData."""
        columns = [
            ColumnDef(
                name="id",
                display_name="ID",
                type=ColumnType.STRING,
                width=8,
                display_style="cyan",
            ),
        ]
        return TableData(
            columns=columns,
            rows=[["TEST-1"]],
            title="Test",
            total_count=1,
            returned_count=1,
        )

    def test_plain_text_formatter(self):
        """Test PlainTextOutputFormatter."""
        table = self.create_table_data()
        formatter = PlainTextOutputFormatter(table)
        result = formatter.format()

        assert isinstance(result, str)
        assert "TEST-1" in result

    def test_json_formatter(self):
        """Test JSONOutputFormatter."""
        import json

        table = self.create_table_data()
        formatter = JSONOutputFormatter(table)
        result = formatter.format()

        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_csv_formatter(self):
        """Test CSVOutputFormatter."""
        table = self.create_table_data()
        formatter = CSVOutputFormatter(table)
        result = formatter.format()

        assert isinstance(result, str)
        assert "ID" in result
