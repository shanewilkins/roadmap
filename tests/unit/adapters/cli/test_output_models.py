"""Unit tests for the structured output data models.

TableData/ColumnDef are pure dataclasses, so these tests build real
instances and assert on concrete values rather than mocking anything.
"""

import pytest

from roadmap.adapters.inbound.cli.models.output_models import (
    ColumnDef,
    ColumnType,
    TableData,
)


def _columns() -> list[ColumnDef]:
    return [
        ColumnDef(name="id", display_name="ID", type=ColumnType.STRING),
        ColumnDef(name="title", display_name="Title", type=ColumnType.STRING),
        ColumnDef(
            name="status",
            display_name="Status",
            type=ColumnType.ENUM,
            enum_values=["open", "closed"],
        ),
    ]


def _table() -> TableData:
    return TableData(
        columns=_columns(),
        rows=[
            ["1", "Fix bug", "open"],
            ["2", "Add feature", "closed"],
            ["3", "Write docs", "open"],
        ],
        title="Issues",
    )


class TestColumnDefRoundtrip:
    @pytest.mark.parametrize(
        "column_type",
        list(ColumnType),
        ids=[member.value for member in ColumnType],
    )
    def test_to_dict_from_dict_roundtrip_preserves_type(
        self, column_type: ColumnType
    ) -> None:
        original = ColumnDef(name="field", display_name="Field", type=column_type)
        restored = ColumnDef.from_dict(original.to_dict())
        assert restored == original

    def test_to_dict_serializes_enum_as_plain_string(self) -> None:
        column = ColumnDef(name="status", display_name="Status", type=ColumnType.ENUM)
        assert column.to_dict()["type"] == "enum"

    def test_from_dict_defaults_display_name_to_name(self) -> None:
        column = ColumnDef.from_dict({"name": "id"})
        assert column.display_name == "id"
        assert column.type is ColumnType.STRING
        assert column.sortable is True
        assert column.filterable is True


class TestTableDataConstruction:
    def test_defaults_counts_from_row_count(self) -> None:
        table = _table()
        assert table.total_count == 3
        assert table.returned_count == 3

    def test_explicit_counts_are_preserved(self) -> None:
        table = TableData(
            columns=_columns(), rows=[["1", "a", "open"]], total_count=100
        )
        assert table.total_count == 100
        assert table.returned_count == 1

    def test_mismatched_row_length_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Row 0 has 2 values but 3 columns"):
            TableData(columns=_columns(), rows=[["1", "only-two"]])


class TestActiveColumnsAndRows:
    def test_active_columns_defaults_to_all_columns(self) -> None:
        table = _table()
        assert [col.name for col in table.active_columns] == ["id", "title", "status"]

    def test_active_columns_respects_selection_order(self) -> None:
        table = _table().select_columns(["status", "id"])
        assert [col.name for col in table.active_columns] == ["status", "id"]

    def test_active_rows_projects_selected_columns_in_order(self) -> None:
        table = _table().select_columns(["status", "id"])
        assert table.active_rows == [["open", "1"], ["closed", "2"], ["open", "3"]]


class TestFilter:
    def test_equality_filter_keeps_matching_rows(self) -> None:
        filtered = _table().filter("status", "open")
        assert [row[0] for row in filtered.rows] == ["1", "3"]
        assert filtered.returned_count == 2
        assert filtered.filters_applied == {"status": "open"}

    def test_list_filter_acts_as_in_clause(self) -> None:
        filtered = _table().filter("id", ["1", "2"])
        assert [row[0] for row in filtered.rows] == ["1", "2"]

    def test_unknown_column_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Column 'nope' not found"):
            _table().filter("nope", "x")

    def test_non_filterable_column_raises_value_error(self) -> None:
        columns = _columns()
        columns[0].filterable = False
        table = TableData(columns=columns, rows=[["1", "a", "open"]])
        with pytest.raises(ValueError, match="Column 'id' is not filterable"):
            table.filter("id", "1")

    def test_invalid_enum_value_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Invalid value 'bogus'"):
            _table().filter("status", "bogus")

    def test_valid_enum_list_values_are_accepted(self) -> None:
        filtered = _table().filter("status", ["open", "closed"])
        assert filtered.returned_count == 3


class TestSort:
    def test_string_spec_sorts_ascending_by_single_column(self) -> None:
        sorted_table = _table().sort("title")
        assert [row[1] for row in sorted_table.rows] == [
            "Add feature",
            "Fix bug",
            "Write docs",
        ]

    def test_desc_direction_reverses_order(self) -> None:
        sorted_table = _table().sort([("title", "desc")])
        assert [row[1] for row in sorted_table.rows] == [
            "Write docs",
            "Fix bug",
            "Add feature",
        ]

    def test_multi_column_sort_breaks_ties_with_second_key(self) -> None:
        table = TableData(
            columns=_columns(),
            rows=[
                ["1", "B", "open"],
                ["2", "A", "open"],
                ["3", "A", "closed"],
            ],
        )
        sorted_table = table.sort([("status", "asc"), ("title", "asc")])
        assert [row[0] for row in sorted_table.rows] == ["3", "2", "1"]

    def test_none_values_sort_last(self) -> None:
        table = TableData(
            columns=_columns(),
            rows=[["1", None, "open"], ["2", "A", "open"]],
        )
        sorted_table = table.sort("title")
        assert [row[0] for row in sorted_table.rows] == ["2", "1"]

    def test_unknown_column_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Column 'nope' not found"):
            _table().sort("nope")

    def test_non_sortable_column_raises_value_error(self) -> None:
        columns = _columns()
        columns[1].sortable = False
        table = TableData(columns=columns, rows=[["1", "a", "open"]])
        with pytest.raises(ValueError, match="Column 'title' is not sortable"):
            table.sort("title")


class TestSelectColumns:
    def test_selecting_unknown_column_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Column 'nope' not found"):
            _table().select_columns(["nope"])

    def test_selection_is_recorded_on_result(self) -> None:
        table = _table().select_columns(["id"])
        assert table.selected_columns == ["id"]
        assert table.rows == _table().rows  # underlying rows untouched


class TestDictRoundtrip:
    def test_to_dict_reflects_active_rows_and_metadata(self) -> None:
        table = _table().select_columns(["id", "status"])
        payload = table.to_dict()
        assert payload["title"] == "Issues"
        assert payload["rows"] == [["1", "open"], ["2", "closed"], ["3", "open"]]
        assert payload["metadata"]["selected_columns"] == ["id", "status"]
        assert payload["metadata"]["total"] == 3

    def test_from_dict_reconstructs_equivalent_table(self) -> None:
        original = _table()
        restored = TableData.from_dict(original.to_dict())
        assert restored.title == original.title
        assert restored.rows == original.rows
        assert [col.name for col in restored.columns] == [
            col.name for col in original.columns
        ]

    def test_from_dict_falls_back_to_description_for_headline(self) -> None:
        restored = TableData.from_dict(
            {"columns": [], "rows": [], "description": "legacy headline"}
        )
        assert restored.headline == "legacy headline"
