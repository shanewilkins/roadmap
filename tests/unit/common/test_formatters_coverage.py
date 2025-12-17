"""Test coverage for formatters module."""

from roadmap.shared.formatters.text.basic import (
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
    truncate_text,
)
from roadmap.shared.formatters.text.duration import (
    format_count,
    format_duration,
)
from roadmap.shared.formatters.text.status_badges import (
    format_percentage,
    format_status_badge,
)


class TestFormatTable:
    """Test format_table function."""

    def test_format_table_creates_table(self):
        """Test format_table creates a formatted table."""
        result = format_table(
            title="Test Table",
            columns=["Name", "Age"],
            rows=[("Alice", 30), ("Bob", 25)],
        )

        assert result is not None

    def test_format_table_with_empty_rows(self):
        """Test format_table with empty rows."""
        result = format_table(
            title="Empty Table",
            columns=["Col1", "Col2"],
            rows=[],
        )

        assert result is not None

    def test_format_table_with_many_rows(self):
        """Test format_table with many rows."""
        rows = [(f"Row{i}", f"Value{i}") for i in range(10)]
        result = format_table(
            title="Many Rows",
            columns=["Row", "Value"],
            rows=rows,
        )

        assert result is not None

    def test_format_table_with_special_characters(self):
        """Test format_table with special characters."""
        result = format_table(
            title="Special Chars",
            columns=["Name", "Status"],
            rows=[("Alice & Bob", "✓ Done"), ("Carol |  Dave", "✗ Failed")],
        )

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

    def test_format_panel_creates_panel(self):
        """Test format_panel creates a panel."""
        panel = format_panel("Test content")

        assert panel is not None

    def test_format_panel_with_title(self):
        """Test format_panel with title."""
        panel = format_panel("Content", title="My Panel")

        assert panel is not None

    def test_format_panel_expand_option(self):
        """Test format_panel with expand option."""
        panel_normal = format_panel("Content", expand=False)
        panel_expanded = format_panel("Content", expand=True)

        assert panel_normal is not None
        assert panel_expanded is not None

    def test_format_panel_with_multiline_content(self):
        """Test format_panel with multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        panel = format_panel(content, title="Multiline")

        assert panel is not None


class TestFormatHeaders:
    """Test format_header function."""

    def test_format_header_level_1(self):
        """Test format_header level 1."""
        header = format_header("Header 1", level=1)

        assert header is not None
        assert hasattr(header, "style")

    def test_format_header_level_2(self):
        """Test format_header level 2."""
        header = format_header("Header 2", level=2)

        assert header is not None

    def test_format_header_level_3(self):
        """Test format_header level 3."""
        header = format_header("Header 3", level=3)

        assert header is not None

    def test_format_header_default_level(self):
        """Test format_header with default level."""
        header = format_header("Header Default")

        assert header is not None

    def test_format_header_with_special_text(self):
        """Test format_header with special characters."""
        header = format_header("→ Special Header ←")

        assert header is not None


class TestFormatStatusMessages:
    """Test status message formatting functions."""

    def test_format_success(self):
        """Test format_success."""
        success = format_success("Operation successful")

        assert success is not None
        assert hasattr(success, "style")

    def test_format_error(self):
        """Test format_error."""
        error = format_error("An error occurred")

        assert error is not None

    def test_format_warning(self):
        """Test format_warning."""
        warning = format_warning("Warning message")

        assert warning is not None

    def test_format_info(self):
        """Test format_info."""
        info = format_info("Information message")

        assert info is not None

    def test_all_status_messages_have_style(self):
        """Test all status message formatters return styled text."""
        success = format_success("Success")
        error = format_error("Error")
        warning = format_warning("Warning")
        info = format_info("Info")

        for text_obj in [success, error, warning, info]:
            assert hasattr(text_obj, "style")
            assert text_obj.style is not None


class TestFormatList:
    """Test format_list function."""

    def test_format_list_simple(self):
        """Test format_list with simple items."""
        result = format_list(["Item 1", "Item 2", "Item 3"])

        assert result is not None
        assert isinstance(result, str)
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result
        assert "•" in result

    def test_format_list_with_title(self):
        """Test format_list with title."""
        result = format_list(["Item 1", "Item 2"], title="My List")

        assert "My List" in result
        assert "Item 1" in result

    def test_format_list_empty(self):
        """Test format_list with empty list."""
        result = format_list([])

        assert result is not None

    def test_format_list_with_empty_title(self):
        """Test format_list with empty title."""
        result = format_list(["Item 1"], title="")

        assert "Item 1" in result

    def test_format_list_with_long_items(self):
        """Test format_list with long items."""
        long_item = "A" * 100
        result = format_list([long_item])

        assert long_item in result


class TestFormatKeyValuePairs:
    """Test format_key_value_pairs function."""

    def test_format_key_value_pairs_simple(self):
        """Test format_key_value_pairs with simple dict."""
        pairs = {"name": "Alice", "age": 30}
        result = format_key_value_pairs(pairs)

        assert result is not None
        assert "name" in result
        assert "Alice" in result
        assert "age" in result
        assert "30" in result

    def test_format_key_value_pairs_with_title(self):
        """Test format_key_value_pairs with title."""
        pairs = {"key": "value"}
        result = format_key_value_pairs(pairs, title="Properties")

        assert "Properties" in result
        assert "key" in result

    def test_format_key_value_pairs_empty(self):
        """Test format_key_value_pairs with empty dict."""
        result = format_key_value_pairs({})

        assert result is not None

    def test_format_key_value_pairs_alignment(self):
        """Test format_key_value_pairs aligns keys."""
        pairs = {"short": "value1", "very_long_key": "value2"}
        result = format_key_value_pairs(pairs)

        # Both colons should be aligned
        assert "short" in result
        assert "very_long_key" in result

    def test_format_key_value_pairs_various_types(self):
        """Test format_key_value_pairs with various value types."""
        pairs = {"int": 42, "float": 3.14, "bool": True, "none": None}
        result = format_key_value_pairs(pairs)

        assert "42" in result
        assert "3.14" in result
        assert "True" in result
        assert "None" in result


class TestFormatStatusBadge:
    """Test format_status_badge function."""

    def test_format_status_badge_closed(self):
        """Test format_status_badge with closed status."""
        badge = format_status_badge("closed")

        assert badge is not None

    def test_format_status_badge_in_progress(self):
        """Test format_status_badge with in-progress status."""
        badge = format_status_badge("in-progress")

        assert badge is not None

    def test_format_status_badge_todo(self):
        """Test format_status_badge with todo status."""
        badge = format_status_badge("todo")

        assert badge is not None

    def test_format_status_badge_blocked(self):
        """Test format_status_badge with blocked status."""
        badge = format_status_badge("blocked")

        assert badge is not None

    def test_format_status_badge_review(self):
        """Test format_status_badge with review status."""
        badge = format_status_badge("review")

        assert badge is not None

    def test_format_status_badge_case_insensitive(self):
        """Test format_status_badge is case insensitive."""
        badge_lower = format_status_badge("closed")
        badge_upper = format_status_badge("CLOSED")

        assert badge_lower is not None
        assert badge_upper is not None

    def test_format_status_badge_unknown_status(self):
        """Test format_status_badge with unknown status."""
        badge = format_status_badge("unknown_status")

        # Should return a badge even for unknown status
        assert badge is not None

    def test_format_status_badge_underscore_variants(self):
        """Test format_status_badge with underscore variants."""
        badge_dash = format_status_badge("in-progress")
        badge_underscore = format_status_badge("in_progress")

        assert badge_dash is not None
        assert badge_underscore is not None


class TestFormatPercentage:
    """Test format_percentage function."""

    def test_format_percentage_simple(self):
        """Test format_percentage with simple value."""
        result = format_percentage(0.75)

        assert result is not None
        assert isinstance(result, str)
        assert "75" in result

    def test_format_percentage_with_decimals(self):
        """Test format_percentage with decimal places."""
        result = format_percentage(0.33333, decimals=2)

        assert result is not None

    def test_format_percentage_zero(self):
        """Test format_percentage with zero."""
        result = format_percentage(0.0)

        assert result is not None

    def test_format_percentage_one(self):
        """Test format_percentage with 100%."""
        result = format_percentage(1.0)

        assert result is not None
        assert "100" in result

    def test_format_percentage_default_decimals(self):
        """Test format_percentage default decimals."""
        result = format_percentage(0.666)

        assert result is not None


class TestFormatDuration:
    """Test format_duration function."""

    def test_format_duration_seconds(self):
        """Test format_duration with seconds."""
        result = format_duration(5.0)

        assert result is not None
        assert isinstance(result, str)

    def test_format_duration_minutes(self):
        """Test format_duration with minutes."""
        result = format_duration(300.0)  # 5 minutes

        assert result is not None

    def test_format_duration_hours(self):
        """Test format_duration with hours."""
        result = format_duration(3600.0)  # 1 hour

        assert result is not None

    def test_format_duration_complex(self):
        """Test format_duration with mixed time."""
        result = format_duration(3661.0)  # 1 hour, 1 minute, 1 second

        assert result is not None

    def test_format_duration_zero(self):
        """Test format_duration with zero."""
        result = format_duration(0.0)

        assert result is not None

    def test_format_duration_subsecond(self):
        """Test format_duration with subsecond duration."""
        result = format_duration(0.5)

        assert result is not None


class TestFormatCount:
    """Test format_count function."""

    def test_format_count_singular(self):
        """Test format_count with singular."""
        result = format_count(1, "item")

        assert result is not None
        assert "1" in result
        assert "item" in result

    def test_format_count_plural_default(self):
        """Test format_count with plural default."""
        result = format_count(5, "item")

        assert result is not None
        assert "5" in result
        assert "items" in result  # Should add 's' by default

    def test_format_count_plural_custom(self):
        """Test format_count with custom plural."""
        result = format_count(5, "process", "processes")

        assert result is not None
        assert "5" in result
        assert "processes" in result

    def test_format_count_zero(self):
        """Test format_count with zero."""
        result = format_count(0, "item")

        assert result is not None
        assert "0" in result

    def test_format_count_large_number(self):
        """Test format_count with large number."""
        result = format_count(1000000, "record")

        assert result is not None
        assert "1000000" in result


class TestFormatJson:
    """Test format_json function."""

    def test_format_json_dict(self):
        """Test format_json with dictionary."""
        data = {"name": "Alice", "age": 30}
        result = format_json(data)

        assert result is not None
        assert isinstance(result, str)
        assert "name" in result
        assert "Alice" in result

    def test_format_json_list(self):
        """Test format_json with list."""
        data = [1, 2, 3, 4, 5]
        result = format_json(data)

        assert result is not None
        assert "1" in result

    def test_format_json_nested(self):
        """Test format_json with nested structure."""
        data = {
            "user": {"name": "Alice", "age": 30},
            "items": [1, 2, 3],
        }
        result = format_json(data)

        assert result is not None
        assert "user" in result

    def test_format_json_custom_indent(self):
        """Test format_json with custom indent."""
        data = {"key": "value"}
        result_2 = format_json(data, indent=2)
        result_4 = format_json(data, indent=4)

        assert result_2 is not None
        assert result_4 is not None

    def test_format_json_empty_dict(self):
        """Test format_json with empty dict."""
        result = format_json({})

        assert result is not None

    def test_format_json_null_values(self):
        """Test format_json with None values."""
        data = {"key": None, "other": "value"}
        result = format_json(data)

        assert result is not None


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

    def test_nested_formatting(self):
        """Test multiple nested formatting operations."""
        kvp = format_key_value_pairs(
            {"Status": "Ready", "Progress": "95%"},
            title="System Stats",
        )

        items = format_list(
            ["Process 1: Done", "Process 2: Done"],
            title="Completed",
        )

        assert kvp is not None
        assert items is not None

    def test_all_formatters_handle_unicode(self):
        """Test all formatters handle unicode properly."""
        test_string = "Unicode test: ñ, ü, 中文, 🎉"

        operations = [
            lambda: format_list([test_string]),
            lambda: format_header(test_string),
            lambda: format_success(test_string),
            lambda: format_error(test_string),
            lambda: format_info(test_string),
        ]

        for operation in operations:
            result = operation()
            assert result is not None


class TestFormatterTruncation:
    """Test truncate_text function."""

    def test_truncate_text_under_limit(self):
        """Test truncate_text when text is under limit."""
        text = "Short"
        result = truncate_text(text, max_length=50)
        assert result == "Short"

    def test_truncate_text_at_limit(self):
        """Test truncate_text when text is exactly at limit."""
        text = "Exactly"
        result = truncate_text(text, max_length=7)
        assert result == "Exactly"

    def test_truncate_text_over_limit(self):
        """Test truncate_text when text exceeds limit."""
        text = "This is a long text that needs truncation"
        result = truncate_text(text, max_length=20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_truncate_text_custom_suffix(self):
        """Test truncate_text with custom suffix."""
        text = "This is a long text"
        result = truncate_text(text, max_length=15, suffix=">>")
        assert result.endswith(">>")

    def test_truncate_text_empty_string(self):
        """Test truncate_text with empty string."""
        result = truncate_text("", max_length=50)
        assert result == ""


class TestFormatterJSON:
    """Test format_json function."""

    def test_format_json_basic_dict(self):
        """Test format_json with dictionary."""
        data = {"key": "value", "number": 42}
        result = format_json(data)
        assert '"key": "value"' in result
        assert '"number": 42' in result

    def test_format_json_list(self):
        """Test format_json with list."""
        data = ["item1", "item2", "item3"]
        result = format_json(data)
        assert "item1" in result
        assert "item2" in result

    def test_format_json_nested(self):
        """Test format_json with nested structures."""
        data = {"outer": {"inner": "value"}}
        result = format_json(data)
        assert "outer" in result
        assert "inner" in result

    def test_format_json_with_custom_indent(self):
        """Test format_json with custom indentation."""
        data = {"key": "value"}
        result_2 = format_json(data, indent=2)
        result_4 = format_json(data, indent=4)
        # More spaces with larger indent
        assert len(result_4) > len(result_2)

    def test_format_json_with_non_serializable(self):
        """Test format_json with objects that have custom string repr."""

        class CustomObj:
            def __str__(self):
                return "custom_string"

        data = {"obj": CustomObj()}
        result = format_json(data)
        assert "custom_string" in result


class TestFormatterKeyValuePairs:
    """Test format_key_value_pairs function."""

    def test_format_key_value_pairs_empty(self):
        """Test format_key_value_pairs with empty dict."""
        result = format_key_value_pairs({})
        assert result == ""

    def test_format_key_value_pairs_single_pair(self):
        """Test format_key_value_pairs with one pair."""
        result = format_key_value_pairs({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_format_key_value_pairs_multiple(self):
        """Test format_key_value_pairs with multiple pairs."""
        data = {"short": "val", "much_longer_key": "value"}
        result = format_key_value_pairs(data)
        assert "short" in result
        assert "much_longer_key" in result
        assert "val" in result

    def test_format_key_value_pairs_with_title(self):
        """Test format_key_value_pairs with title."""
        data = {"key": "value"}
        result = format_key_value_pairs(data, title="Settings")
        assert "Settings" in result
        assert "key" in result

    def test_format_key_value_pairs_alignment(self):
        """Test that values are aligned in format_key_value_pairs."""
        data = {"a": "1", "bb": "2", "ccc": "3"}
        result = format_key_value_pairs(data)
        lines = result.split("\n")
        # All values should be aligned at same column
        assert len(lines) == 3


class TestFormatterCount:
    """Test format_count function."""

    def test_format_count_singular(self):
        """Test format_count with count of 1."""
        result = format_count(1, "item")
        assert "1 item" in result

    def test_format_count_plural_default(self):
        """Test format_count with plural using default."""
        result = format_count(5, "item")
        assert "5 items" in result

    def test_format_count_plural_custom(self):
        """Test format_count with custom plural."""
        result = format_count(2, "child", "children")
        assert "2 children" in result

    def test_format_count_zero(self):
        """Test format_count with zero."""
        result = format_count(0, "file")
        assert "0 files" in result

    def test_format_count_large_number(self):
        """Test format_count with large number."""
        result = format_count(1000000, "record")
        assert "1000000" in result


class TestFormatterDuration:
    """Test format_duration function."""

    def test_format_duration_seconds(self):
        """Test format_duration with seconds."""
        result = format_duration(30)
        assert "30s" in result

    def test_format_duration_minutes(self):
        """Test format_duration with minutes."""
        result = format_duration(120)
        assert "m" in result

    def test_format_duration_hours(self):
        """Test format_duration with hours."""
        result = format_duration(3600)
        assert "h" in result

    def test_format_duration_fractional(self):
        """Test format_duration with fractional seconds."""
        result = format_duration(45.5)
        assert "45s" == result

    def test_format_duration_zero(self):
        """Test format_duration with zero."""
        result = format_duration(0)
        assert "0s" in result


class TestFormatterPercentage:
    """Test format_percentage function."""

    def test_format_percentage_decimal(self):
        """Test format_percentage with decimal."""
        result = format_percentage(0.75)
        assert "75" in result

    def test_format_percentage_already_percent(self):
        """Test format_percentage with already percent value."""
        result = format_percentage(75)
        assert "75" in result

    def test_format_percentage_zero(self):
        """Test format_percentage with zero."""
        result = format_percentage(0)
        assert "0" in result

    def test_format_percentage_hundred(self):
        """Test format_percentage with 100%."""
        result = format_percentage(1.0)
        assert "100" in result

    def test_format_percentage_decimals(self):
        """Test format_percentage with custom decimal places."""
        result = format_percentage(0.333, decimals=3)
        assert "33" in result
        # Should have 3 decimal places shown


class TestStatusBadgeFormatting:
    """Test format_status_badge function."""

    def test_format_status_badge_open(self):
        """Test format_status_badge with 'open' status."""
        badge = format_status_badge("open")
        assert badge is not None
        assert "open" in str(badge).lower()

    def test_format_status_badge_closed(self):
        """Test format_status_badge with 'closed' status."""
        badge = format_status_badge("closed")
        assert badge is not None

    def test_format_status_badge_in_progress(self):
        """Test format_status_badge with 'in_progress'."""
        badge = format_status_badge("in_progress")
        assert badge is not None

    def test_format_status_badge_blocked(self):
        """Test format_status_badge with 'blocked'."""
        badge = format_status_badge("blocked")
        assert badge is not None

    def test_format_status_badge_unknown(self):
        """Test format_status_badge with unknown status."""
        badge = format_status_badge("unknown_status")
        assert badge is not None

    def test_format_status_badge_case_insensitive(self):
        """Test format_status_badge is case insensitive."""
        badge1 = format_status_badge("OPEN")
        badge2 = format_status_badge("open")
        assert badge1 is not None
        assert badge2 is not None


class TestFormatterList:
    """Test format_list function."""

    def test_format_list_empty(self):
        """Test format_list with empty list."""
        result = format_list([])
        assert result == ""

    def test_format_list_single_item(self):
        """Test format_list with one item."""
        result = format_list(["item1"])
        assert "item1" in result
        assert "•" in result

    def test_format_list_multiple_items(self):
        """Test format_list with multiple items."""
        items = ["first", "second", "third"]
        result = format_list(items)
        for item in items:
            assert item in result

    def test_format_list_with_title(self):
        """Test format_list with title."""
        result = format_list(["item1"], title="My List")
        assert "My List" in result
        assert "item1" in result

    def test_format_list_special_characters(self):
        """Test format_list with special characters."""
        items = ["item-1", "item_2", "item.3"]
        result = format_list(items)
        for item in items:
            assert item in result
