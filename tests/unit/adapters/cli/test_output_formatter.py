"""Unit tests for OutputFormatter and its format-specific wrapper classes.

All formats are exercised against real TableData instances; no mocking is
needed since formatting is pure data-in/string-out (or Table-out) logic.
"""

import json

import pytest

from roadmap.adapters.inbound.cli.models.output_models import ColumnDef, TableData
from roadmap.adapters.inbound.cli.output_formatter import (
    CSVOutputFormatter,
    HTMLOutputFormatter,
    JSONOutputFormatter,
    OutputFormatter,
    PlainTextOutputFormatter,
)


def _columns() -> list[ColumnDef]:
    return [
        ColumnDef(name="id", display_name="ID"),
        ColumnDef(name="title", display_name="Title"),
    ]


def _table() -> TableData:
    return TableData(
        columns=_columns(),
        rows=[["1", "Fix ✅ bug"], ["2", None]],
        title="Issues",
    )


def _empty_table() -> TableData:
    return TableData(columns=_columns(), rows=[])


class TestToRich:
    def test_sets_title_and_column_headers(self) -> None:
        rich_table = OutputFormatter(_table()).to_rich()
        assert rich_table.title == "Issues"
        assert [col.header for col in rich_table.columns] == ["ID", "Title"]

    def test_renders_none_as_dash_placeholder(self) -> None:
        rich_table = OutputFormatter(_table()).to_rich()
        title_cells = rich_table.columns[1]._cells
        assert title_cells == ["Fix ✅ bug", "-"]

    def test_respects_selected_columns(self) -> None:
        table = _table().select_columns(["title"])
        rich_table = OutputFormatter(table).to_rich()
        assert [col.header for col in rich_table.columns] == ["Title"]


class TestToPlainText:
    def test_includes_title_header_separator_and_rows(self) -> None:
        text = OutputFormatter(_table()).to_plain_text()
        lines = text.splitlines()
        assert lines[0] == "Issues"
        assert lines[1] == ""
        assert lines[2].startswith("ID")
        assert set(lines[3]) == {"-", "+"}
        assert "1" in lines[4]

    def test_replaces_emoji_with_ascii_equivalent(self) -> None:
        text = OutputFormatter(_table()).to_plain_text()
        assert "✅" not in text
        assert "[OK]" in text

    def test_none_value_renders_as_dash(self) -> None:
        text = OutputFormatter(_table()).to_plain_text()
        rows_section = text.splitlines()[5]
        assert "-" in rows_section


class TestToJson:
    def test_matches_table_to_dict(self) -> None:
        table = _table()
        parsed = json.loads(OutputFormatter(table).to_json())
        assert parsed == table.to_dict()

    def test_none_values_survive_as_json_null(self) -> None:
        parsed = json.loads(OutputFormatter(_table()).to_json())
        assert parsed["rows"][1] == ["2", None]


class TestToCsv:
    def test_header_and_rows_are_comma_separated(self) -> None:
        text = OutputFormatter(_table()).to_csv()
        lines = text.splitlines()
        assert lines[0] == "ID,Title"
        assert lines[1] == "1,Fix ✅ bug"

    def test_none_values_render_as_empty_string(self) -> None:
        text = OutputFormatter(_table()).to_csv()
        assert text.splitlines()[2] == "2,"

    def test_values_with_commas_are_quoted(self) -> None:
        table = TableData(columns=_columns(), rows=[["1", "a, b"]])
        text = OutputFormatter(table).to_csv()
        assert '"a, b"' in text.splitlines()[1]


class TestToMarkdown:
    def test_produces_pipe_delimited_table_with_title_heading(self) -> None:
        text = OutputFormatter(_table()).to_markdown()
        lines = text.splitlines()
        assert lines[0] == "## Issues"
        assert "| ID | Title |" in lines
        assert lines[lines.index("| ID | Title |") + 1].startswith("|---")

    def test_none_values_render_as_empty_string(self) -> None:
        text = OutputFormatter(_table()).to_markdown()
        assert "| 2 |  |" in text.splitlines()


class TestToHtml:
    def test_includes_title_and_all_cell_values(self) -> None:
        html = OutputFormatter(_table()).to_html()
        assert "<h1>Issues</h1>" in html
        assert "<th>ID</th>" in html
        assert "<td>1</td>" in html

    def test_escapes_html_special_characters(self) -> None:
        table = TableData(columns=_columns(), rows=[["1", "<script>&'\"</script>"]])
        html = OutputFormatter(table).to_html()
        assert "<script>" not in html
        assert "&lt;script&gt;&amp;&#39;&quot;&lt;/script&gt;" in html


@pytest.mark.parametrize(
    "method_name", ["to_plain_text", "to_csv", "to_markdown", "to_html"]
)
def test_empty_table_returns_empty_string_for_every_text_format(
    method_name: str,
) -> None:
    formatter = OutputFormatter(_empty_table())
    assert getattr(formatter, method_name)() == ""


class TestSpecializedFormatterWrappers:
    def test_plain_text_wrapper_delegates_to_to_plain_text(self) -> None:
        table = _table()
        assert (
            PlainTextOutputFormatter(table).format()
            == OutputFormatter(table).to_plain_text()
        )

    def test_json_wrapper_delegates_to_to_json(self) -> None:
        table = _table()
        assert JSONOutputFormatter(table).format() == OutputFormatter(table).to_json()

    def test_csv_wrapper_delegates_to_to_csv(self) -> None:
        table = _table()
        assert CSVOutputFormatter(table).format() == OutputFormatter(table).to_csv()

    def test_html_wrapper_delegates_to_to_html(self) -> None:
        table = _table()
        wrapped = HTMLOutputFormatter(table).format()
        direct = OutputFormatter(table).to_html()

        def without_footer(html: str) -> list[str]:
            # Both embed a live "Generated <timestamp>" footer line.
            return [
                line for line in html.splitlines() if not line.startswith("<p class=")
            ]

        assert without_footer(wrapped) == without_footer(direct)
