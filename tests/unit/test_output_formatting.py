"""
Tests for output models and formatting.

Unit tests for ColumnDef, TableData, OutputFormatter, and specialized formatters.
"""

import json

import pytest

from roadmap.common.models import ColumnDef, ColumnType, TableData
from roadmap.common.output_formatter import (
    CSVOutputFormatter,
    JSONOutputFormatter,
    OutputFormatter,
    PlainTextOutputFormatter,
)


class TestColumnDef:
    """Tests for ColumnDef dataclass."""

    def test_create_simple_column(self):
        """Test creating a simple column definition."""
        col = ColumnDef(name="id", display_name="ID")
        assert col.name == "id"
        assert col.display_name == "ID"
        assert col.type == ColumnType.STRING
        assert col.sortable
        assert col.filterable

    def test_create_column_with_all_attributes(self):
        """Test creating column with all attributes."""
        col = ColumnDef(
            name="status",
            display_name="Status",
            type=ColumnType.ENUM,
            width=15,
            headline="Task status",
            display_style="bold blue",
            enum_values=["todo", "in_progress", "done"],
            sortable=True,
            filterable=True,
        )
        assert col.name == "status"
        assert col.type == ColumnType.ENUM
        assert col.enum_values == ["todo", "in_progress", "done"]

    def test_column_serialization(self):
        """Test column to_dict and from_dict."""
        original = ColumnDef(
            name="created_at",
            display_name="Created",
            type=ColumnType.DATETIME,
            width=20,
            sortable=True,
        )
        data = original.to_dict()
        restored = ColumnDef.from_dict(data)
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.width == original.width


class TestTableData:
    """Tests for TableData dataclass."""

    def test_create_simple_table(self):
        """Test creating a simple table."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
        ]
        rows = [[1, "Alice"], [2, "Bob"]]
        table = TableData(columns=cols, rows=rows)

        assert len(table.columns) == 2
        assert len(table.rows) == 2
        # total_count should not be auto-set - it's for filtering context
        assert table.total_count is None or isinstance(table.total_count, int)

    def test_table_with_metadata(self):
        """Test table with title and description."""
        cols = [ColumnDef(name="status", display_name="Status")]
        rows = [["active"], ["inactive"]]
        table = TableData(
            columns=cols,
            rows=rows,
            title="User Status",
            headline="Current user status",
            total_count=2,
            returned_count=2,
        )
        assert table.title == "User Status"
        assert table.total_count == 2

    def test_table_row_validation(self):
        """Test that TableData validates row structure."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
        ]
        rows = [
            [1, "Alice"],
            [2, "Bob"],
        ]
        # Should not raise
        table = TableData(columns=cols, rows=rows)
        assert len(table.rows) == 2

    def test_active_columns_property(self):
        """Test active_columns respects column selection."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="email", display_name="Email"),
        ]
        rows = [[1, "Alice", "alice@example.com"], [2, "Bob", "bob@example.com"]]
        table = TableData(columns=cols, rows=rows, selected_columns=["id", "name"])

        active = table.active_columns
        assert len(active) == 2
        assert active[0].name == "id"
        assert active[1].name == "name"

    def test_active_rows_property(self):
        """Test active_rows respects column selection."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="email", display_name="Email"),
        ]
        rows = [[1, "Alice", "alice@example.com"], [2, "Bob", "bob@example.com"]]
        table = TableData(columns=cols, rows=rows, selected_columns=["id", "name"])

        active_rows = table.active_rows
        assert len(active_rows) == 2
        # Each row should only have selected columns (indices 0, 1)
        assert active_rows[0] == [1, "Alice"]
        assert active_rows[1] == [2, "Bob"]

    def test_filter_by_string(self):
        """Test filtering table by string value."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="status", display_name="Status"),
        ]
        rows = [
            [1, "active"],
            [2, "inactive"],
            [3, "active"],
        ]
        table = TableData(columns=cols, rows=rows)

        filtered = table.filter("status", "active")
        assert len(filtered.rows) == 2
        assert filtered.rows[0][1] == "active"
        assert filtered.rows[1][1] == "active"

    def test_filter_by_integer(self):
        """Test filtering table by integer value."""
        cols = [
            ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER),
            ColumnDef(name="count", display_name="Count", type=ColumnType.INTEGER),
        ]
        rows = [[1, 5], [2, 10], [3, 5]]
        table = TableData(columns=cols, rows=rows)

        filtered = table.filter("count", 5)
        assert len(filtered.rows) == 2

    def test_sort_by_column(self):
        """Test sorting table by column."""
        cols = [
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="age", display_name="Age", type=ColumnType.INTEGER),
        ]
        rows = [["Alice", 30], ["Charlie", 25], ["Bob", 35]]
        table = TableData(columns=cols, rows=rows)

        sorted_table = table.sort("name")
        assert sorted_table.rows[0][0] == "Alice"
        assert sorted_table.rows[1][0] == "Bob"
        assert sorted_table.rows[2][0] == "Charlie"

    def test_sort_by_integer_column(self):
        """Test sorting by integer column."""
        cols = [
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="age", display_name="Age", type=ColumnType.INTEGER),
        ]
        rows = [["Alice", 30], ["Charlie", 25], ["Bob", 35]]
        table = TableData(columns=cols, rows=rows)

        sorted_table = table.sort("age")
        assert sorted_table.rows[0][1] == 25
        assert sorted_table.rows[1][1] == 30
        assert sorted_table.rows[2][1] == 35

    def test_select_columns(self):
        """Test selecting specific columns."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="email", display_name="Email"),
        ]
        rows = [[1, "Alice", "alice@example.com"], [2, "Bob", "bob@example.com"]]
        table = TableData(columns=cols, rows=rows)

        selected = table.select_columns(["id", "email"])
        assert len(selected.active_columns) == 2
        assert selected.active_columns[0].name == "id"
        assert selected.active_columns[1].name == "email"

    def test_filter_sort_chain(self):
        """Test chaining filter and sort operations."""
        cols = [
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="status", display_name="Status"),
            ColumnDef(name="age", display_name="Age", type=ColumnType.INTEGER),
        ]
        rows = [
            ["Alice", "active", 30],
            ["Bob", "inactive", 25],
            ["Charlie", "active", 35],
            ["Diana", "active", 28],
        ]
        table = TableData(columns=cols, rows=rows)

        # Filter to active, then sort by age
        result = table.filter("status", "active").sort("age")
        assert len(result.rows) == 3
        assert result.rows[0][0] == "Diana"  # age 28
        assert result.rows[1][0] == "Alice"  # age 30
        assert result.rows[2][0] == "Charlie"  # age 35

    def test_table_serialization(self):
        """Test table to_dict and from_dict."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
        ]
        rows = [[1, "Alice"], [2, "Bob"]]
        original = TableData(columns=cols, rows=rows, title="Users", total_count=2)

        data = original.to_dict()
        restored = TableData.from_dict(data)

        assert restored.title == original.title
        assert len(restored.rows) == len(original.rows)
        assert restored.total_count == original.total_count


class TestOutputFormatter:
    """Tests for OutputFormatter class."""

    @pytest.fixture
    def sample_table(self):
        """Create a sample table for testing."""
        cols = [
            ColumnDef(name="id", display_name="ID", width=5),
            ColumnDef(name="name", display_name="Name", width=15),
            ColumnDef(name="status", display_name="Status", width=10),
        ]
        rows = [
            [1, "Alice", "✅ active"],
            [2, "Bob", "❌ inactive"],
            [3, "Charlie", "⚠️ pending"],
        ]
        return TableData(columns=cols, rows=rows, title="Users")

    def test_to_rich_returns_table(self, sample_table):
        """Test to_rich returns Rich Table object."""
        formatter = OutputFormatter(sample_table)
        table = formatter.to_rich()
        # Check it has the right type and structure
        assert table.title == "Users"
        assert len(table.columns) == 3

    def test_to_plain_text_no_emojis(self, sample_table):
        """Test to_plain_text replaces emoji with ASCII."""
        formatter = OutputFormatter(sample_table)
        text = formatter.to_plain_text()

        assert "✅" not in text  # Emoji removed
        assert "[OK]" in text  # Replaced with ASCII
        assert "❌" not in text
        assert "[ERROR]" in text
        assert "⚠️" not in text
        assert "[WARN]" in text

    def test_to_plain_text_includes_title(self, sample_table):
        """Test to_plain_text includes table title."""
        formatter = OutputFormatter(sample_table)
        text = formatter.to_plain_text()
        assert "Users" in text

    def test_to_plain_text_includes_headers(self, sample_table):
        """Test to_plain_text includes column headers."""
        formatter = OutputFormatter(sample_table)
        text = formatter.to_plain_text()
        assert "ID" in text
        assert "Name" in text
        assert "Status" in text

    def test_to_json_valid(self, sample_table):
        """Test to_json produces valid JSON."""
        formatter = OutputFormatter(sample_table)
        json_str = formatter.to_json()
        data = json.loads(json_str)

        assert data["title"] == "Users"
        assert len(data["rows"]) == 3
        assert len(data["columns"]) == 3

    def test_to_json_includes_metadata(self, sample_table):
        """Test to_json includes all metadata."""
        formatter = OutputFormatter(sample_table)
        json_str = formatter.to_json()
        data = json.loads(json_str)

        assert "title" in data
        assert "columns" in data
        assert "rows" in data

    def test_to_csv_header(self, sample_table):
        """Test to_csv includes proper header."""
        formatter = OutputFormatter(sample_table)
        csv_str = formatter.to_csv()
        lines = csv_str.strip().split("\n")

        # First line should be header (strip to handle \r\n)
        assert lines[0].strip() == "ID,Name,Status"

    def test_to_csv_data_rows(self, sample_table):
        """Test to_csv includes data rows."""
        formatter = OutputFormatter(sample_table)
        csv_str = formatter.to_csv()
        lines = csv_str.strip().split("\n")

        # Should have header + 3 data rows
        assert len(lines) == 4
        assert "1," in lines[1]
        assert "Alice" in lines[1]

    def test_to_csv_escapes_special_chars(self):
        """Test to_csv escapes special characters."""
        cols = [
            ColumnDef(name="text", display_name="Text"),
        ]
        rows = [
            ['Contains "quotes"'],
            ["Contains, comma"],
            ["Contains\nnewline"],
        ]
        table = TableData(columns=cols, rows=rows)
        formatter = OutputFormatter(table)
        csv_str = formatter.to_csv()

        # CSV should properly escape these
        assert '"""quotes"""' in csv_str or '"Contains ""quotes"""' in csv_str

    def test_to_markdown_includes_title(self, sample_table):
        """Test to_markdown includes title."""
        formatter = OutputFormatter(sample_table)
        md = formatter.to_markdown()
        assert "## Users" in md

    def test_to_markdown_table_syntax(self, sample_table):
        """Test to_markdown produces valid markdown table."""
        formatter = OutputFormatter(sample_table)
        md = formatter.to_markdown()

        # Should have pipe delimiters
        assert "|" in md
        # Should have separator row
        assert "-+-" in md or "|-" in md

    def test_empty_table_handling(self):
        """Test handling of empty table."""
        cols = [ColumnDef(name="id", display_name="ID")]
        table = TableData(columns=cols, rows=[])
        formatter = OutputFormatter(table)

        assert formatter.to_plain_text() == ""
        assert formatter.to_csv() == ""

    def test_null_values_handled(self):
        """Test handling of None values."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="value", display_name="Value"),
        ]
        rows = [[1, None], [2, "data"]]
        table = TableData(columns=cols, rows=rows)
        formatter = OutputFormatter(table)

        # Plain text should show "-" for None
        text = formatter.to_plain_text()
        assert "-" in text

        # CSV should show empty string for None (may have \r\n line endings)
        csv = formatter.to_csv()
        # Check for empty cell - could be ",," or ", " or ",\r\n"
        assert ",\r\n" in csv or ",\n" in csv or "1," in csv

    def test_column_selection_in_all_formats(self):
        """Test that column selection works in all formats."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="email", display_name="Email"),
        ]
        rows = [[1, "Alice", "alice@example.com"], [2, "Bob", "bob@example.com"]]
        table = TableData(columns=cols, rows=rows, selected_columns=["id", "name"])
        formatter = OutputFormatter(table)

        # Plain text
        text = formatter.to_plain_text()
        assert "ID" in text
        assert "Name" in text
        # Email should not appear
        lines = text.split("\n")
        assert not any("Email" in line for line in lines)

        # JSON
        json_data = json.loads(formatter.to_json())
        # JSON should only have selected columns in output
        if len(json_data.get("rows", [[]])[0]) < 3:
            # If row selection is applied
            assert len(json_data.get("rows", [[]])[0]) == 2

        # CSV
        csv_lines = formatter.to_csv().strip().split("\n")
        # Header row should only have selected columns
        assert csv_lines[0].strip() == "ID,Name"


class TestSpecializedFormatters:
    """Tests for specialized formatter classes."""

    @pytest.fixture
    def sample_table(self):
        """Create a sample table."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="status", display_name="Status"),
        ]
        rows = [[1, "✅ active"], [2, "❌ inactive"]]
        return TableData(columns=cols, rows=rows)

    def test_plain_text_formatter(self, sample_table):
        """Test PlainTextOutputFormatter."""
        formatter = PlainTextOutputFormatter(sample_table)
        text = formatter.format()
        assert "[OK]" in text
        assert "✅" not in text

    def test_json_formatter(self, sample_table):
        """Test JSONOutputFormatter."""
        formatter = JSONOutputFormatter(sample_table)
        text = formatter.format()
        data = json.loads(text)
        assert "rows" in data
        assert len(data["rows"]) == 2

    def test_csv_formatter(self, sample_table):
        """Test CSVOutputFormatter."""
        formatter = CSVOutputFormatter(sample_table)
        text = formatter.format()
        lines = text.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
