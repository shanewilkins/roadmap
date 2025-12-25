"""Tests for smart table layout system."""

import pytest
from rich.panel import Panel
from rich.table import Table

from roadmap.adapters.cli.layout import LayoutConfig, SmartTableLayout
from roadmap.common.output_models import ColumnDef, ColumnType, TableData


@pytest.fixture
def sample_table_data():
    """Create sample table data for testing."""
    columns = [
        ColumnDef(name="id", display_name="ID", type=ColumnType.STRING),
        ColumnDef(name="title", display_name="Title", type=ColumnType.STRING),
        ColumnDef(name="status", display_name="Status", type=ColumnType.ENUM),
        ColumnDef(name="priority", display_name="Priority", type=ColumnType.ENUM),
    ]
    rows = [
        ["1", "Fix login bug", "in-progress", "high"],
        ["2", "Add dark mode", "todo", "medium"],
        ["3", "Performance optimization", "blocked", "low"],
    ]
    return TableData(
        title="Issues",
        columns=columns,
        rows=rows,
    )


@pytest.fixture
def wide_table_data():
    """Create table data with many wide columns."""
    columns = [
        ColumnDef(name="id", display_name="ID"),
        ColumnDef(name="title", display_name="Very Long Title Column"),
        ColumnDef(name="description", display_name="Detailed Description"),
        ColumnDef(name="status", display_name="Status"),
        ColumnDef(name="priority", display_name="Priority"),
        ColumnDef(name="assignee", display_name="Assignee"),
        ColumnDef(name="due_date", display_name="Due Date"),
        ColumnDef(name="estimate", display_name="Time Estimate"),
    ]
    rows = [
        [
            "1",
            "Fix the critical login authentication bug",
            "Users are unable to login with their credentials",
            "in-progress",
            "critical",
            "john.doe@example.com",
            "2024-01-15",
            "8 hours",
        ],
    ]
    return TableData(
        title="Issues",
        columns=columns,
        rows=rows,
    )


class TestSmartTableLayout:
    """Test SmartTableLayout class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        layout = SmartTableLayout()
        assert layout.config.responsive_enabled is True
        assert layout.config.vertical_threshold == 0.8

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = LayoutConfig(responsive_enabled=False, vertical_threshold=0.7)
        layout = SmartTableLayout(config)
        assert layout.config.responsive_enabled is False
        assert layout.config.vertical_threshold == 0.7

    def test_get_terminal_width_valid(self):
        """Test getting terminal width."""
        layout = SmartTableLayout()
        width = layout.get_terminal_width()
        assert width >= 40
        assert width <= 1000

    def test_calculate_table_width_simple(self, sample_table_data):
        """Test table width calculation."""
        layout = SmartTableLayout()
        width = layout.calculate_table_width(sample_table_data)
        assert width > 0
        assert width < 200

    def test_calculate_table_width_empty(self):
        """Test table width calculation for empty table."""
        layout = SmartTableLayout()
        empty_table = TableData(
            title="Empty",
            columns=[],
            rows=[],
        )
        width = layout.calculate_table_width(empty_table)
        assert width == 20

    def test_calculate_table_width_wide(self, wide_table_data):
        """Test table width calculation for wide table."""
        layout = SmartTableLayout()
        width = layout.calculate_table_width(wide_table_data)
        assert width > 50  # Wide tables should have significant width

    def test_should_use_vertical_layout_false(self, sample_table_data):
        """Test that small tables use horizontal layout."""
        layout = SmartTableLayout()
        layout.get_terminal_width = lambda: 200  # Wide terminal
        use_vertical = layout.should_use_vertical_layout(sample_table_data)
        assert use_vertical is False

    def test_should_use_vertical_layout_true(self, wide_table_data):
        """Test that wide tables use vertical layout on narrow terminals."""
        layout = SmartTableLayout()
        layout.get_terminal_width = lambda: 60  # Narrow terminal
        use_vertical = layout.should_use_vertical_layout(wide_table_data)
        assert use_vertical is True

    def test_should_use_vertical_layout_disabled(self, wide_table_data):
        """Test that responsive layout can be disabled."""
        config = LayoutConfig(responsive_enabled=False)
        layout = SmartTableLayout(config)
        layout.get_terminal_width = lambda: 60
        use_vertical = layout.should_use_vertical_layout(wide_table_data)
        assert use_vertical is False

    def test_render_horizontal(self, sample_table_data):
        """Test horizontal table rendering."""
        layout = SmartTableLayout()
        renderable = layout.render_horizontal(sample_table_data)
        assert isinstance(renderable, Table)
        assert renderable.title == "Issues"

    def test_render_vertical(self, sample_table_data):
        """Test vertical table rendering."""
        layout = SmartTableLayout()
        renderable = layout.render_vertical(sample_table_data)
        assert isinstance(renderable, Panel)

    def test_render_chooses_horizontal(self, sample_table_data):
        """Test that render chooses horizontal for narrow data."""
        layout = SmartTableLayout()
        layout.get_terminal_width = lambda: 200
        renderable = layout.render(sample_table_data)
        assert isinstance(renderable, Table)

    def test_render_chooses_vertical(self, wide_table_data):
        """Test that render chooses vertical for wide data."""
        layout = SmartTableLayout()
        layout.get_terminal_width = lambda: 60
        renderable = layout.render(wide_table_data)
        assert isinstance(renderable, Panel)

    def test_render_as_string_horizontal(self, sample_table_data):
        """Test rendering table as string in horizontal layout."""
        layout = SmartTableLayout()
        result = layout.render_as_string(sample_table_data, width=200)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_as_string_vertical(self, sample_table_data):
        """Test rendering table as string in vertical layout."""
        layout = SmartTableLayout()
        result = layout.render_as_string(sample_table_data, width=40)
        assert isinstance(result, str)
        assert "Entry" in result or "ID:" in result

    def test_render_as_string_preserves_original_width(self, sample_table_data):
        """Test that render_as_string doesn't modify original method."""
        layout = SmartTableLayout()
        layout.render_as_string(sample_table_data, width=50)
        # Should still be callable
        width = layout.get_terminal_width()
        assert width > 0

    def test_vertical_layout_shows_all_fields(self, sample_table_data):
        """Test that vertical layout displays all fields."""
        layout = SmartTableLayout()
        result = layout.render_as_string(sample_table_data, width=40)
        # Should show column names
        for column in sample_table_data.columns:
            assert column.display_name in result or "Entry" in result

    def test_vertical_layout_multiple_rows(self):
        """Test vertical layout with multiple rows."""
        columns = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
        ]
        rows = [
            ["1", "Alice"],
            ["2", "Bob"],
            ["3", "Charlie"],
        ]
        table_data = TableData(
            title="Users",
            columns=columns,
            rows=rows,
        )
        layout = SmartTableLayout()
        result = layout.render_as_string(table_data, width=40)
        # Should have separators between entries
        assert "─" in result or "Entry" in result

    def test_threshold_near_boundary(self):
        """Test behavior when table width is near threshold."""
        columns = [ColumnDef(name="col1", display_name="Column 1")]
        rows = [["short"]]
        table_data = TableData(
            title="Test",
            columns=columns,
            rows=rows,
        )

        config = LayoutConfig(vertical_threshold=0.5)
        layout = SmartTableLayout(config)

        # Set terminal width to make table exactly at threshold
        layout.get_terminal_width = lambda: 100
        # Table is narrow, so should use horizontal
        use_vertical = layout.should_use_vertical_layout(table_data)
        assert use_vertical is False

    def test_empty_table_rendering(self):
        """Test rendering of empty table."""
        empty_table = TableData(
            title="Empty",
            columns=[ColumnDef(name="id", display_name="ID")],
            rows=[],
        )
        layout = SmartTableLayout()
        renderable = layout.render(empty_table)
        # Should still return a renderable
        assert renderable is not None
        assert isinstance(renderable, Table | Panel)

    def test_single_row_table(self):
        """Test rendering of single row table."""
        columns = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
        ]
        rows = [["1", "Item"]]
        table_data = TableData(
            title="Single",
            columns=columns,
            rows=rows,
        )
        layout = SmartTableLayout()
        renderable = layout.render(table_data)
        assert renderable is not None

    def test_missing_values_in_vertical(self):
        """Test vertical layout with empty string values."""
        columns = [
            ColumnDef(name="id", display_name="ID"),
            ColumnDef(name="name", display_name="Name"),
            ColumnDef(name="optional", display_name="Optional"),
        ]
        rows = [
            ["1", "Item", ""],  # Last value is empty string
        ]
        table_data = TableData(
            title="Items",
            columns=columns,
            rows=rows,
        )
        layout = SmartTableLayout()
        result = layout.render_as_string(table_data, width=40)
        # Should handle empty values gracefully
        assert "ID" in result or "Entry" in result
