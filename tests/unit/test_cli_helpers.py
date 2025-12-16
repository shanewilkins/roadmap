"""
Tests for CLI helpers - format handling, column selection, sorting, filtering.
"""

import click
import pytest

from roadmap.common.cli_helpers import (
    ColumnSelector,
    FilterSpec,
    FilterSpecParser,
    OutputFormatHandler,
    SortSpecParser,
)
from roadmap.common.output_models import ColumnDef, ColumnType, TableData


class TestOutputFormatHandler:
    """Tests for OutputFormatHandler."""

    @pytest.fixture
    def sample_table(self):
        """Create a sample table."""
        cols = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="status", display_name="Status"),
        ]
        rows = [
            [1, "Alice", "active"],
            [2, "Bob", "inactive"],
        ]
        return TableData(columns=cols, rows=rows, title="Users")

    def test_render_plain_format(self, sample_table):
        """Test rendering plain-text format."""
        output = OutputFormatHandler.render(sample_table, "plain")
        assert isinstance(output, str)
        assert "ID" in output
        assert "Alice" in output

    def test_render_json_format(self, sample_table):
        """Test rendering JSON format."""
        output = OutputFormatHandler.render(sample_table, "json")
        assert isinstance(output, str)
        assert '"title"' in output or "'title'" in output

    def test_render_csv_format(self, sample_table):
        """Test rendering CSV format."""
        output = OutputFormatHandler.render(sample_table, "csv")
        assert isinstance(output, str)
        assert "ID" in output
        assert "Alice" in output

    def test_render_markdown_format(self, sample_table):
        """Test rendering Markdown format."""
        output = OutputFormatHandler.render(sample_table, "markdown")
        assert isinstance(output, str)
        assert "|" in output  # Markdown table delimiter

    def test_render_rich_format(self, sample_table):
        """Test rendering Rich format (returns Table object)."""
        output = OutputFormatHandler.render(sample_table, "rich")
        # Rich returns a Table object
        assert hasattr(output, "title")

    def test_render_invalid_format(self, sample_table):
        """Test error on invalid format."""
        with pytest.raises(ValueError, match="Unknown format"):
            OutputFormatHandler.render(sample_table, "invalid")

    def test_supported_formats(self):
        """Test SUPPORTED_FORMATS dictionary."""
        formats = OutputFormatHandler.SUPPORTED_FORMATS
        assert "rich" in formats
        assert "plain" in formats
        assert "json" in formats
        assert "csv" in formats
        assert "markdown" in formats


class TestColumnSelector:
    """Tests for ColumnSelector utility."""

    def test_parse_single_column(self):
        """Test parsing single column."""
        available = ["id", "name", "email"]
        result = ColumnSelector.parse("name", available)
        assert result == ["name"]

    def test_parse_multiple_columns(self):
        """Test parsing multiple columns."""
        available = ["id", "name", "email"]
        result = ColumnSelector.parse("id,name", available)
        assert result == ["id", "name"]

    def test_parse_with_spaces(self):
        """Test parsing with spaces around commas."""
        available = ["id", "name", "email"]
        result = ColumnSelector.parse("id , name , email", available)
        assert result == ["id", "name", "email"]

    def test_parse_case_insensitive(self):
        """Test case-insensitive matching."""
        available = ["id", "name", "email"]
        result = ColumnSelector.parse("ID,NAME", available)
        assert result == ["id", "name"]

    def test_parse_respects_order(self):
        """Test that column order is preserved."""
        available = ["id", "name", "email"]
        result = ColumnSelector.parse("email,id,name", available)
        assert result == ["email", "id", "name"]

    def test_parse_unknown_column(self):
        """Test error on unknown column."""
        available = ["id", "name", "email"]
        with pytest.raises(click.BadParameter, match="Unknown column"):
            ColumnSelector.parse("unknown", available)

    def test_parse_none_returns_none(self):
        """Test that None input returns None."""
        available = ["id", "name", "email"]
        result = ColumnSelector.parse(None, available)
        assert result is None

    def test_parse_empty_string_returns_none(self):
        """Test that empty string returns None."""
        available = ["id", "name", "email"]
        result = ColumnSelector.parse("", available)
        assert result is None

    def test_get_help_text(self):
        """Test help text generation."""
        available = ["id", "name"]
        help_text = ColumnSelector.get_help_text(available)
        assert "id" in help_text
        assert "name" in help_text


class TestSortSpecParser:
    """Tests for SortSpecParser."""

    def test_parse_single_column_default_asc(self):
        """Test single column sorting (default ascending)."""
        available = ["name", "age", "status"]
        result = SortSpecParser.parse("name", available)
        assert result == [("name", "asc")]

    def test_parse_single_column_explicit_asc(self):
        """Test single column with explicit ascending."""
        available = ["name", "age", "status"]
        result = SortSpecParser.parse("name:asc", available)
        assert result == [("name", "asc")]

    def test_parse_single_column_desc(self):
        """Test single column descending."""
        available = ["name", "age", "status"]
        result = SortSpecParser.parse("name:desc", available)
        assert result == [("name", "desc")]

    def test_parse_multiple_columns(self):
        """Test multiple column sorting."""
        available = ["name", "age", "status"]
        result = SortSpecParser.parse("status:asc,name:desc", available)
        assert result == [("status", "asc"), ("name", "desc")]

    def test_parse_mixed_directions(self):
        """Test mixed sort directions."""
        available = ["name", "age", "status"]
        result = SortSpecParser.parse("status,name:desc,age:asc", available)
        assert result == [("status", "asc"), ("name", "desc"), ("age", "asc")]

    def test_parse_case_insensitive(self):
        """Test case-insensitive column names."""
        available = ["name", "age", "status"]
        result = SortSpecParser.parse("NAME:DESC", available)
        assert result == [("name", "desc")]

    def test_parse_with_spaces(self):
        """Test parsing with spaces."""
        available = ["name", "age", "status"]
        result = SortSpecParser.parse("name : desc , age : asc", available)
        assert result == [("name", "desc"), ("age", "asc")]

    def test_parse_unknown_column(self):
        """Test error on unknown column."""
        available = ["name", "age"]
        with pytest.raises(click.BadParameter, match="Unknown sort column"):
            SortSpecParser.parse("unknown", available)

    def test_parse_invalid_direction(self):
        """Test error on invalid direction."""
        available = ["name", "age"]
        with pytest.raises(click.BadParameter, match="Invalid sort direction"):
            SortSpecParser.parse("name:invalid", available)

    def test_parse_none_returns_none(self):
        """Test that None input returns None."""
        available = ["name", "age"]
        result = SortSpecParser.parse(None, available)
        assert result is None

    def test_get_help_text(self):
        """Test help text generation."""
        help_text = SortSpecParser.get_help_text()
        assert "asc" in help_text
        assert "desc" in help_text


class TestFilterSpecParser:
    """Tests for FilterSpecParser."""

    def test_parse_equality_string(self):
        """Test equality filter on string."""
        column_types = {"status": ColumnType.STRING}
        result = FilterSpecParser.parse("status=open", column_types)
        assert result is not None
        assert len(result) == 1
        assert result[0].column == "status"
        assert result[0].operator == "="
        assert result[0].value == "open"

    def test_parse_inequality(self):
        """Test inequality filter."""
        column_types = {"status": ColumnType.STRING}
        result = FilterSpecParser.parse("status!=closed", column_types)
        assert result is not None
        assert len(result) == 1
        assert result[0].operator == "!="

    def test_parse_comparison_integer(self):
        """Test comparison filters with integer."""
        column_types = {"count": ColumnType.INTEGER}
        result = FilterSpecParser.parse("count>=5", column_types)
        assert result is not None
        assert result[0].operator == ">="
        assert result[0].value == 5
        assert isinstance(result[0].value, int)

    def test_parse_comparison_float(self):
        """Test comparison filters with float."""
        column_types = {"rating": ColumnType.FLOAT}
        result = FilterSpecParser.parse("rating>3.5", column_types)
        assert result is not None
        assert result[0].value == 3.5
        assert isinstance(result[0].value, float)

    def test_parse_regex_filter(self):
        """Test regex filter."""
        column_types = {"title": ColumnType.STRING}
        result = FilterSpecParser.parse("title~bug", column_types)
        assert result is not None
        assert result[0].operator == "~"
        assert result[0].value == "bug"

    def test_parse_multiple_filters(self):
        """Test multiple filters."""
        column_types = {"status": ColumnType.STRING, "count": ColumnType.INTEGER}
        result = FilterSpecParser.parse("status=open,count>=5", column_types)
        assert result is not None
        assert len(result) == 2

    def test_parse_boolean_true(self):
        """Test boolean filter - true variants."""
        column_types = {"active": ColumnType.BOOLEAN}
        for val in ["true", "True", "TRUE", "yes", "1", "on"]:
            result = FilterSpecParser.parse(f"active={val}", column_types)
            assert result is not None
            assert result[0].value is True

    def test_parse_boolean_false(self):
        """Test boolean filter - false variants."""
        column_types = {"active": ColumnType.BOOLEAN}
        for val in ["false", "False", "FALSE", "no", "0", "off"]:
            result = FilterSpecParser.parse(f"active={val}", column_types)
            assert result is not None
            assert result[0].value is False

    def test_parse_case_insensitive_column(self):
        """Test case-insensitive column names."""
        column_types = {"status": ColumnType.STRING}
        result = FilterSpecParser.parse("STATUS=open", column_types)
        assert result is not None
        assert result[0].column == "status"

    def test_parse_unknown_column(self):
        """Test error on unknown column."""
        column_types = {"status": ColumnType.STRING}
        with pytest.raises(click.BadParameter, match="Unknown filter column"):
            FilterSpecParser.parse("unknown=value", column_types)

    def test_parse_invalid_integer(self):
        """Test error on invalid integer."""
        column_types = {"count": ColumnType.INTEGER}
        with pytest.raises(click.BadParameter, match="Expected integer"):
            FilterSpecParser.parse("count=notanumber", column_types)

    def test_parse_invalid_float(self):
        """Test error on invalid float."""
        column_types = {"rating": ColumnType.FLOAT}
        with pytest.raises(click.BadParameter, match="Expected float"):
            FilterSpecParser.parse("rating=notanumber", column_types)

    def test_parse_invalid_boolean(self):
        """Test error on invalid boolean."""
        column_types = {"active": ColumnType.BOOLEAN}
        with pytest.raises(click.BadParameter, match="Expected boolean"):
            FilterSpecParser.parse("active=maybe", column_types)

    def test_parse_invalid_syntax(self):
        """Test error on invalid filter syntax."""
        column_types = {"status": ColumnType.STRING}
        with pytest.raises(click.BadParameter, match="Invalid filter syntax"):
            FilterSpecParser.parse("status", column_types)

    def test_parse_none_returns_none(self):
        """Test that None input returns None."""
        column_types = {"status": ColumnType.STRING}
        result = FilterSpecParser.parse(None, column_types)
        assert result is None

    def test_parse_with_spaces(self):
        """Test parsing with spaces."""
        column_types = {"status": ColumnType.STRING}
        result = FilterSpecParser.parse(" status = open ", column_types)
        assert result is not None
        assert result[0].value == "open"

    def test_get_help_text(self):
        """Test help text generation."""
        help_text = FilterSpecParser.get_help_text()
        assert "column" in help_text.lower()
        assert "=" in help_text


class TestFilterSpec:
    """Tests for FilterSpec dataclass."""

    def test_create_filter_spec(self):
        """Test creating a filter spec."""
        spec = FilterSpec("status", "=", "open")
        assert spec.column == "status"
        assert spec.operator == "="
        assert spec.value == "open"

    def test_filter_spec_repr(self):
        """Test filter spec string representation."""
        spec = FilterSpec("count", ">=", 5)
        assert "count" in repr(spec)
        assert ">=" in repr(spec)
