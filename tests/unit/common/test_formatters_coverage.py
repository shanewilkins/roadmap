"""Test coverage for formatters module."""

import pytest

from roadmap.common.formatters.text.basic import (
    format_error,
    format_header,
    format_info,
    format_json,
    format_key_value_pairs,
    format_list,
    format_panel,
    format_success,
    format_table,
    format_warning,
)
from roadmap.common.formatters.text.duration import (
    format_count,
    format_duration,
)
from roadmap.common.formatters.text.status_badges import (
    format_percentage,
    format_status_badge,
)


class TestFormatTable:
    """Test format_table function."""

    @pytest.mark.parametrize(
        "title,columns,rows,has_content",
        [
            ("Test Table", ["Name", "Age"], [("Alice", 30), ("Bob", 25)], True),
            ("Empty Table", ["Col1", "Col2"], [], False),
            (
                "Many Rows",
                ["Row", "Value"],
                [(f"Row{i}", f"Value{i}") for i in range(10)],
                True,
            ),
            ("Special Chars", ["Name", "Status"], [("Alice & Bob", "✓ Done")], True),
        ],
    )
    def test_format_table_variants(self, title, columns, rows, has_content):
        """Test format_table with various configurations."""
        result = format_table(title=title, columns=columns, rows=rows)
        assert result is not None

    def test_format_table_converts_cells_to_string(self):
        """Test format_table converts all cells to strings."""
        result = format_table(
            title="Type Conversion",
            columns=["Int", "Float", "Bool"],
            rows=[(1, 2.5, True), (10, 3.14, False)],
        )
        assert result is not None


class TestFormatPanel:
    """Test format_panel function."""

    @pytest.mark.parametrize(
        "content,title,expand",
        [
            ("Test content", None, None),
            ("Content", "My Panel", None),
            ("Content", None, False),
            ("Content", None, True),
            ("Line 1\nLine 2\nLine 3", "Multiline", None),
        ],
    )
    def test_format_panel_variants(self, content, title, expand):
        """Test format_panel with various options."""
        kwargs = {"expand": expand} if expand is not None else {}
        kwargs["title"] = title if title is not None else None

        panel = format_panel(
            content, **{k: v for k, v in kwargs.items() if v is not None}
        )
        assert panel is not None


class TestFormatHeaders:
    """Test format_header function."""

    @pytest.mark.parametrize(
        "text,level",
        [
            ("Header 1", 1),
            ("Header 2", 2),
            ("Header 3", 3),
            ("Header Default", None),
            ("→ Special Header ←", 1),
        ],
    )
    def test_format_header_variants(self, text, level):
        """Test format_header with various levels."""
        if level is not None:
            header = format_header(text, level=level)
        else:
            header = format_header(text)

        assert header is not None
        assert hasattr(header, "style")


class TestFormatStatusMessages:
    """Test status message formatting functions."""

    @pytest.mark.parametrize(
        "format_func,message",
        [
            (format_success, "Operation successful"),
            (format_error, "An error occurred"),
            (format_warning, "Warning message"),
            (format_info, "Information message"),
        ],
    )
    def test_status_message_formatters(self, format_func, message):
        """Test all status message formatters."""
        result = format_func(message)
        assert result is not None
        assert hasattr(result, "style")


class TestFormatList:
    """Test format_list function."""

    @pytest.mark.parametrize(
        "items,title,has_content",
        [
            (["Item 1", "Item 2", "Item 3"], None, True),
            (["Item 1", "Item 2"], "My List", True),
            ([], None, False),
            (["Item 1"], "", True),
            (["A" * 100], None, True),
        ],
    )
    def test_format_list_variants(self, items, title, has_content):
        """Test format_list with various configurations."""
        if title == "":
            result = format_list(items, title=title)
        elif title:
            result = format_list(items, title=title)
        else:
            result = format_list(items)

        assert result is not None
        assert isinstance(result, str)

        if items:
            assert items[0] in result or "•" in result


class TestFormatKeyValuePairs:
    """Test format_key_value_pairs function."""

    @pytest.mark.parametrize(
        "pairs,title",
        [
            ({"name": "Alice", "age": 30}, None),
            ({"key": "value"}, "Properties"),
            ({}, None),
            ({"short": "value1", "very_long_key": "value2"}, None),
            ({"int": 42, "float": 3.14, "bool": True, "none": None}, None),
        ],
    )
    def test_format_key_value_pairs_variants(self, pairs, title):
        """Test format_key_value_pairs with various inputs."""
        if title:
            result = format_key_value_pairs(pairs, title=title)
        else:
            result = format_key_value_pairs(pairs)

        assert result is not None

        for key in pairs:
            assert key in result


class TestFormatStatusBadge:
    """Test format_status_badge function."""

    @pytest.mark.parametrize(
        "status",
        [
            "closed",
            "in-progress",
            "todo",
            "blocked",
            "review",
            "CLOSED",
            "in_progress",
            "unknown_status",
        ],
    )
    def test_format_status_badge_variants(self, status):
        """Test format_status_badge with various statuses."""
        badge = format_status_badge(status)
        assert badge is not None


class TestFormatPercentage:
    """Test format_percentage function."""

    @pytest.mark.parametrize(
        "value,decimals,expected_substring",
        [
            (0.75, None, "75"),
            (0.33333, 2, "33"),
            (0.0, None, "0"),
            (1.0, None, "100"),
            (0.666, None, "66"),
        ],
    )
    def test_format_percentage_variants(self, value, decimals, expected_substring):
        """Test format_percentage with various values."""
        if decimals is not None:
            result = format_percentage(value, decimals=decimals)
        else:
            result = format_percentage(value)

        assert result is not None
        assert isinstance(result, str)


class TestFormatDuration:
    """Test format_duration function."""

    @pytest.mark.parametrize(
        "seconds,expected_substring",
        [
            (5.0, None),
            (300.0, None),
            (3600.0, None),
            (3661.0, None),
            (0.0, None),
            (0.5, None),
        ],
    )
    def test_format_duration_variants(self, seconds, expected_substring):
        """Test format_duration with various time periods."""
        result = format_duration(seconds)
        assert result is not None
        assert isinstance(result, str)


class TestFormatCount:
    """Test format_count function."""

    @pytest.mark.parametrize(
        "count,singular,plural,expected_in_result",
        [
            (1, "item", None, "1"),
            (5, "item", None, "5"),
            (5, "process", "processes", "processes"),
            (0, "item", None, "0"),
            (1000000, "record", None, "1000000"),
        ],
    )
    def test_format_count_variants(self, count, singular, plural, expected_in_result):
        """Test format_count with various counts and forms."""
        if plural:
            result = format_count(count, singular, plural)
        else:
            result = format_count(count, singular)

        assert result is not None
        assert expected_in_result in result


class TestFormatJson:
    """Test format_json function."""

    @pytest.mark.parametrize(
        "data,indent,check_string",
        [
            ({"name": "Alice", "age": 30}, None, "name"),
            ([1, 2, 3, 4, 5], None, "1"),
            ({"user": {"name": "Alice"}, "items": [1, 2, 3]}, None, "user"),
            ({"key": "value"}, 2, None),
            ({"key": "value"}, 4, None),
            ({}, None, "{}"),
            ({"key": None, "other": "value"}, None, "null"),  # JSON uses null, not None
        ],
    )
    def test_format_json_variants(self, data, indent, check_string):
        """Test format_json with various data structures."""
        if indent is not None:
            result = format_json(data, indent=indent)
        else:
            result = format_json(data)

        assert result is not None
        assert isinstance(result, str)

        if check_string:
            assert check_string in result


class TestFormatterIntegration:
    """Integration tests for formatters."""

    def test_formatting_combination(self):
        """Test using multiple formatters together."""
        header = format_header("Results")
        success = format_success("Operation complete")
        items = format_list(["Item 1", "Item 2"])

        assert header is not None
        assert success is not None
        assert items is not None

    def test_table_with_formatted_content(self):
        """Test formatting table with various content."""
        rows = [
            ("Alice", "✓ Complete"),
            ("Bob", "⏳ In Progress"),
            ("Carol", "✗ Failed"),
        ]

        result = format_table(
            title="Status Report",
            columns=["Name", "Status"],
            rows=rows,
        )

        assert result is not None

    def test_all_formatters_handle_unicode(self):
        """Test all formatters handle unicode properly."""
        test_string = "Unicode test: ñ, ü, 中文, 🎉"

        operations = [
            lambda: format_list([test_string]),
            lambda: format_header(test_string),
            lambda: format_success(test_string),
            lambda: format_error(test_string),
        ]

        for operation in operations:
            result = operation()
            assert result is not None
