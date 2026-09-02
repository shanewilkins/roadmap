"""Unit tests for CLI output-option parsing helpers (columns/sort/filter/format).

All of these are pure parsing/validation functions, so tests build real
inputs and assert on the concrete parsed results or the specific
click.BadParameter messages raised - no mocking required.
"""

import click
import pytest
from rich.table import Table

from roadmap.adapters.inbound.cli.models.output_models import ColumnType, TableData
from roadmap.adapters.inbound.cli.output_options import (
    ColumnSelector,
    FilterSpec,
    FilterSpecParser,
    OutputFormatHandler,
    SortSpecParser,
    format_output,
)


def _table() -> TableData:
    from roadmap.adapters.inbound.cli.models.output_models import ColumnDef

    return TableData(
        columns=[
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="title", display_name="Title"),
        ],
        rows=[["1", "Fix bug"]],
        title="Issues",
    )


class TestOutputFormatHandlerRender:
    def test_rich_format_returns_rich_table(self) -> None:
        result = OutputFormatHandler.render(_table(), "rich")
        assert isinstance(result, Table)

    @pytest.mark.parametrize(
        "format_name,method_name",
        [
            ("plain", "to_plain_text"),
            ("json", "to_json"),
            ("csv", "to_csv"),
            ("markdown", "to_markdown"),
        ],
    )
    def test_text_formats_delegate_to_matching_formatter_method(
        self, format_name, method_name
    ) -> None:
        from roadmap.adapters.inbound.cli.output_formatter import OutputFormatter

        table = _table()
        rendered = OutputFormatHandler.render(table, format_name)
        expected = getattr(OutputFormatter(table), method_name)()
        assert rendered == expected

    def test_unknown_format_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown format: xml"):
            OutputFormatHandler.render(_table(), "xml")


class TestColumnSelector:
    @pytest.mark.parametrize("empty_value", [None, ""])
    def test_returns_none_when_not_specified(self, empty_value) -> None:
        assert ColumnSelector.parse(empty_value, ["id", "title"]) is None

    def test_normalizes_case_and_preserves_requested_order(self) -> None:
        result = ColumnSelector.parse("TITLE, id", ["id", "title", "status"])
        assert result == ["title", "id"]

    def test_unknown_column_raises_bad_parameter_listing_available(self) -> None:
        with pytest.raises(click.BadParameter, match="Unknown column: nope"):
            ColumnSelector.parse("nope", ["id", "title"])

    def test_help_text_lists_available_columns(self) -> None:
        text = ColumnSelector.get_help_text(["id", "title"])
        assert "id, title" in text


class TestSortSpecParser:
    @pytest.mark.parametrize("empty_value", [None, ""])
    def test_returns_none_when_not_specified(self, empty_value) -> None:
        assert SortSpecParser.parse(empty_value, ["id", "title"]) is None

    def test_single_column_defaults_to_ascending(self) -> None:
        assert SortSpecParser.parse("title", ["id", "title"]) == [("title", "asc")]

    def test_explicit_direction_is_lowercased(self) -> None:
        assert SortSpecParser.parse("title:DESC", ["id", "title"]) == [
            ("title", "desc")
        ]

    def test_multiple_columns_preserve_order(self) -> None:
        result = SortSpecParser.parse("title:desc,id", ["id", "title"])
        assert result == [("title", "desc"), ("id", "asc")]

    def test_unknown_column_raises_bad_parameter(self) -> None:
        with pytest.raises(click.BadParameter, match="Unknown sort column: nope"):
            SortSpecParser.parse("nope", ["id"])

    def test_invalid_direction_raises_bad_parameter(self) -> None:
        with pytest.raises(click.BadParameter, match="Invalid sort direction"):
            SortSpecParser.parse("title:sideways", ["title"])

    def test_help_text_documents_format(self) -> None:
        assert "col1:asc,col2:desc" in SortSpecParser.get_help_text()


class TestFilterSpec:
    def test_repr_shows_column_operator_and_value(self) -> None:
        spec = FilterSpec("status", "=", "open")
        assert repr(spec) == "FilterSpec(status=open)"


class TestFilterSpecParser:
    @pytest.mark.parametrize("empty_value", [None, ""])
    def test_returns_none_when_not_specified(self, empty_value) -> None:
        assert (
            FilterSpecParser.parse(empty_value, {"status": ColumnType.STRING}) is None
        )

    @pytest.mark.parametrize(
        "expression,expected_operator,expected_value",
        [
            ("status=open", "=", "open"),
            ("status!=open", "!=", "open"),
            ("count<=5", "<=", "5"),
            ("count>=5", ">=", "5"),
            ("count<5", "<", "5"),
            ("count>5", ">", "5"),
            ("title~bug", "~", "bug"),
        ],
    )
    def test_operator_is_detected_correctly(
        self, expression, expected_operator, expected_value
    ) -> None:
        column_types = {
            "status": ColumnType.STRING,
            "count": ColumnType.STRING,
            "title": ColumnType.STRING,
        }
        specs = FilterSpecParser.parse(expression, column_types)
        assert specs is not None
        [spec] = specs
        assert spec.operator == expected_operator
        assert spec.value == expected_value

    def test_multiple_comma_separated_filters_are_all_parsed(self) -> None:
        column_types = {"status": ColumnType.STRING, "priority": ColumnType.STRING}
        specs = FilterSpecParser.parse("status=open,priority=high", column_types)
        assert specs is not None
        assert [(s.column, s.value) for s in specs] == [
            ("status", "open"),
            ("priority", "high"),
        ]

    def test_column_name_matching_is_case_insensitive(self) -> None:
        specs = FilterSpecParser.parse("STATUS=open", {"status": ColumnType.STRING})
        assert specs is not None
        [spec] = specs
        assert spec.column == "status"

    def test_unknown_column_raises_bad_parameter(self) -> None:
        with pytest.raises(click.BadParameter, match="Unknown filter column: nope"):
            FilterSpecParser.parse("nope=1", {"status": ColumnType.STRING})

    def test_missing_operator_raises_bad_parameter(self) -> None:
        with pytest.raises(click.BadParameter, match="Invalid filter syntax"):
            FilterSpecParser.parse("statusopen", {"status": ColumnType.STRING})

    @pytest.mark.parametrize(
        "col_type,value_str,expected",
        [
            (ColumnType.INTEGER, "5", 5),
            (ColumnType.FLOAT, "5.5", 5.5),
            (ColumnType.BOOLEAN, "true", True),
            (ColumnType.BOOLEAN, "yes", True),
            (ColumnType.BOOLEAN, "1", True),
            (ColumnType.BOOLEAN, "on", True),
            (ColumnType.BOOLEAN, "false", False),
            (ColumnType.BOOLEAN, "no", False),
            (ColumnType.BOOLEAN, "0", False),
            (ColumnType.BOOLEAN, "off", False),
            (ColumnType.STRING, "hello", "hello"),
            (ColumnType.ENUM, "open", "open"),
        ],
    )
    def test_value_parsing_is_type_aware(self, col_type, value_str, expected) -> None:
        specs = FilterSpecParser.parse(f"col={value_str}", {"col": col_type})
        assert specs is not None
        [spec] = specs
        assert spec.value == expected
        assert type(spec.value) is type(expected)

    @pytest.mark.parametrize(
        "col_type,value_str,message",
        [
            (ColumnType.INTEGER, "notanumber", "Expected integer value"),
            (ColumnType.FLOAT, "notafloat", "Expected float value"),
            (ColumnType.BOOLEAN, "maybe", "Expected boolean value"),
        ],
    )
    def test_invalid_typed_values_raise_bad_parameter(
        self, col_type, value_str, message
    ) -> None:
        with pytest.raises(click.BadParameter, match=message):
            FilterSpecParser.parse(f"col={value_str}", {"col": col_type})

    def test_help_text_documents_operators(self) -> None:
        text = FilterSpecParser.get_help_text()
        assert "!=" in text
        assert "~" in text


class TestFormatOutputDecorator:
    def test_non_table_data_result_passes_through_unchanged(self) -> None:
        @format_output()
        def command() -> str:
            return "plain string"

        assert command() == "plain string"

    def test_table_data_result_is_rendered_per_format_choice(self) -> None:
        from roadmap.adapters.inbound.cli.output_formatter import OutputFormatter

        @format_output(format_choice="json")
        def command() -> TableData:
            return _table()

        rendered = command()
        assert rendered == OutputFormatter(_table()).to_json()

    def test_rich_format_choice_returns_rich_table(self) -> None:
        @format_output(format_choice="rich")
        def command() -> TableData:
            return _table()

        assert isinstance(command(), Table)

    def test_columns_argument_selects_subset_before_rendering(self) -> None:
        import json

        @format_output(format_choice="json", columns=["title"])
        def command() -> TableData:
            return _table()

        parsed = json.loads(command())  # type: ignore[arg-type]
        assert [col["name"] for col in parsed["columns"]] == ["id", "title"]
        assert parsed["metadata"]["selected_columns"] == ["title"]
        assert parsed["rows"] == [["Fix bug"]]
