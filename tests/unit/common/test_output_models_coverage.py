"""Comprehensive tests for output_models module."""

import pytest

from roadmap.common.output_models import (
    ColumnDef,
    ColumnType,
    TableData,
)


class TestColumnType:
    """Tests for ColumnType enum."""

    def test_column_types_basic_types_exist(self):
        """Test that basic column types exist."""
        assert hasattr(ColumnType, "STRING")
        assert hasattr(ColumnType, "INTEGER")
        assert hasattr(ColumnType, "FLOAT")

    def test_column_types_boolean_and_date_types_exist(self):
        """Test that boolean and date column types exist."""
        assert hasattr(ColumnType, "BOOLEAN")
        assert hasattr(ColumnType, "DATE")
        assert hasattr(ColumnType, "DATETIME")

    def test_column_types_enum_type_exists(self):
        """Test that enum column type exists."""
        assert hasattr(ColumnType, "ENUM")

    def test_column_type_values_basic(self):
        """Test that basic column types have correct values."""
        assert ColumnType.STRING.value == "string"
        assert ColumnType.INTEGER.value == "integer"
        assert ColumnType.FLOAT.value == "float"

    def test_column_type_values_boolean_and_date(self):
        """Test that boolean and date types have correct values."""
        assert ColumnType.BOOLEAN.value == "boolean"
        assert ColumnType.DATE.value == "date"
        assert ColumnType.DATETIME.value == "datetime"

    def test_column_type_values_enum(self):
        """Test that enum type has correct value."""
        assert ColumnType.ENUM.value == "enum"

    def test_column_type_string_comparison(self):
        """Test that ColumnType works with string comparison."""
        assert ColumnType.STRING == "string"
        assert ColumnType.INTEGER == "integer"


class TestColumnDef:
    """Tests for ColumnDef dataclass."""

    def test_create_basic_column(self):
        """Test creating a basic column definition."""
        col = ColumnDef(
            name="id",
            display_name="ID",
            type=ColumnType.INTEGER,
        )
        assert col.name == "id"
        assert col.display_name == "ID"
        assert col.type == ColumnType.INTEGER

    def test_create_column_with_width(self):
        """Test creating column with custom width."""
        col = ColumnDef(
            name="name",
            display_name="Name",
            type=ColumnType.STRING,
            width=30,
        )
        assert col.width == 30

    def test_create_enum_column(self):
        """Test creating an ENUM type column."""
        col = ColumnDef(
            name="status",
            display_name="Status",
            type=ColumnType.ENUM,
            enum_values=["open", "closed", "pending"],
        )
        assert col.type == ColumnType.ENUM
        assert col.enum_values == ["open", "closed", "pending"]

    def test_create_column_with_description(self):
        """Test creating column with description."""
        col = ColumnDef(
            name="priority",
            display_name="Priority",
            type=ColumnType.INTEGER,
            description="Issue priority level (1-5)",
        )
        assert col.description == "Issue priority level (1-5)"

    def test_column_alignment(self):
        """Test column display style."""
        col_default = ColumnDef(
            name="name",
            display_name="Name",
            type=ColumnType.STRING,
        )
        col_styled = ColumnDef(
            name="count",
            display_name="Count",
            type=ColumnType.INTEGER,
            display_style="cyan",
        )
        assert col_default.display_style is None
        assert col_styled.display_style == "cyan"

    def test_column_sorting(self):
        """Test column sortable flag."""
        sortable_col = ColumnDef(
            name="name",
            display_name="Name",
            type=ColumnType.STRING,
            sortable=True,
        )
        non_sortable_col = ColumnDef(
            name="action",
            display_name="Action",
            type=ColumnType.STRING,
            sortable=False,
        )
        assert sortable_col.sortable
        assert not non_sortable_col.sortable

    def test_column_visibility(self):
        """Test column filterable flag."""
        filterable_col = ColumnDef(
            name="name",
            display_name="Name",
            type=ColumnType.STRING,
            filterable=True,
        )
        non_filterable_col = ColumnDef(
            name="action",
            display_name="Action",
            type=ColumnType.STRING,
            filterable=False,
        )
        assert filterable_col.filterable
        assert not non_filterable_col.filterable

    def test_column_style_and_description(self):
        """Test column with style and description."""
        col = ColumnDef(
            name="date",
            display_name="Date",
            type=ColumnType.DATE,
            display_style="yellow",
            description="Creation date",
        )
        assert col.display_style == "yellow"
        assert col.description == "Creation date"


class TestTableData:
    """Tests for TableData dataclass."""

    def test_create_basic_table(self):
        """Test creating a basic table."""
        columns = [
            ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER),
            ColumnDef(name="name", display_name="Name", type=ColumnType.STRING),
        ]
        rows = [[1, "Alice"], [2, "Bob"]]

        table = TableData(columns=columns, rows=rows)

        assert len(table.columns) == 2
        assert len(table.rows) == 2
        assert table.title is None
        assert table.description is None

    def test_create_table_with_title_and_description(self):
        """Test creating table with title and description."""
        columns = [ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER)]
        rows = [[1], [2]]

        table = TableData(
            columns=columns,
            rows=rows,
            title="Test Table",
            description="A table for testing",
        )

        assert table.title == "Test Table"
        assert table.description == "A table for testing"

    def test_table_with_filters(self):
        """Test table with applied filters."""
        columns = [
            ColumnDef(name="status", display_name="Status", type=ColumnType.STRING)
        ]
        rows = [["open"], ["closed"]]

        table = TableData(
            columns=columns,
            rows=rows,
            filters_applied={"status": "open"},
        )

        assert table.filters_applied["status"] == "open"

    def test_table_with_sorting(self):
        """Test table with sort specification."""
        columns = [
            ColumnDef(name="priority", display_name="Priority", type=ColumnType.INTEGER)
        ]
        rows = [[1], [3], [2]]

        table = TableData(
            columns=columns,
            rows=rows,
            sort_by=[("priority", "asc")],
        )

        assert len(table.sort_by) == 1
        assert table.sort_by[0] == ("priority", "asc")

    def test_table_with_column_selection(self):
        """Test table with selected columns."""
        columns = [
            ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER),
            ColumnDef(name="name", display_name="Name", type=ColumnType.STRING),
            ColumnDef(name="email", display_name="Email", type=ColumnType.STRING),
        ]
        rows = [[1, "Alice", "alice@example.com"], [2, "Bob", "bob@example.com"]]

        table = TableData(
            columns=columns,
            rows=rows,
            selected_columns=["id", "name"],
        )

        assert table.selected_columns == ["id", "name"]

    def test_table_with_pagination_info(self):
        """Test table with total and returned counts."""
        columns = [ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER)]
        rows = [[1], [2], [3]]

        table = TableData(
            columns=columns,
            rows=rows,
            total_count=100,
            returned_count=3,
        )

        assert table.total_count == 100
        assert table.returned_count == 3

    def test_table_validation_row_length(self):
        """Test table validates row structure during initialization."""
        columns = [
            ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER),
            ColumnDef(name="name", display_name="Name", type=ColumnType.STRING),
        ]
        # Row with wrong number of columns should be caught in __post_init__
        rows = [[1, "Alice", "extra"]]  # 3 values but only 2 columns

        with pytest.raises(ValueError):
            TableData(columns=columns, rows=rows)

    def test_table_empty_rows(self):
        """Test creating table with no rows."""
        columns = [ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER)]
        rows = []

        table = TableData(columns=columns, rows=rows)

        assert len(table.rows) == 0
        assert len(table.columns) == 1

    def test_table_complex_example(self):
        """Test complex table with multiple features."""
        columns = [
            ColumnDef(
                name="id",
                display_name="Issue ID",
                type=ColumnType.INTEGER,
                width=10,
                sortable=True,
            ),
            ColumnDef(
                name="title",
                display_name="Title",
                type=ColumnType.STRING,
                width=40,
                sortable=True,
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.ENUM,
                enum_values=["open", "closed", "pending"],
                sortable=False,
                filterable=True,
            ),
            ColumnDef(
                name="priority",
                display_name="Priority",
                type=ColumnType.INTEGER,
                sortable=True,
                display_style="cyan",
            ),
            ColumnDef(
                name="internal_id",
                display_name="Internal ID",
                type=ColumnType.STRING,
                filterable=False,
            ),
        ]

        rows = [
            [1, "Fix bug", "open", 1, "internal_1"],
            [2, "Add feature", "closed", 2, "internal_2"],
            [3, "Refactor code", "pending", 3, "internal_3"],
        ]

        table = TableData(
            columns=columns,
            rows=rows,
            title="Issues Tracker",
            description="Current status of all issues",
            sort_by=[("priority", "asc")],
            filters_applied={"status": "open", "priority": 1},
            selected_columns=["id", "title", "status", "priority"],
            total_count=1000,
            returned_count=3,
        )

        assert len(table.columns) == 5
        assert len(table.rows) == 3
        assert table.title == "Issues Tracker"
        assert table.selected_columns is not None
        assert len(table.selected_columns) == 4
        assert table.total_count == 1000


class TestOutputModelsIntegration:
    """Integration tests for output models."""

    def test_column_definitions_match_row_data(self):
        """Test that column definitions align with row data structure."""
        columns = [
            ColumnDef(name="id", display_name="ID", type=ColumnType.INTEGER),
            ColumnDef(name="active", display_name="Active", type=ColumnType.BOOLEAN),
            ColumnDef(name="score", display_name="Score", type=ColumnType.FLOAT),
        ]

        rows = [
            [1, True, 95.5],
            [2, False, 87.3],
            [3, True, 92.1],
        ]

        table = TableData(columns=columns, rows=rows)

        # Verify structure
        assert len(table.columns) == 3
        assert len(table.rows) == 3
        for row in table.rows:
            assert len(row) == len(columns)

    def test_enum_column_with_valid_values(self):
        """Test enum column with valid enumerated values."""
        status_col = ColumnDef(
            name="status",
            display_name="Status",
            type=ColumnType.ENUM,
            enum_values=["pending", "approved", "rejected"],
        )

        columns = [status_col]
        rows = [["pending"], ["approved"], ["rejected"]]

        table = TableData(columns=columns, rows=rows)
        assert table.columns[0].enum_values == ["pending", "approved", "rejected"]

    def test_multiple_sort_specifications(self):
        """Test table with multiple sort specifications."""
        columns = [
            ColumnDef(
                name="department", display_name="Department", type=ColumnType.STRING
            ),
            ColumnDef(name="salary", display_name="Salary", type=ColumnType.INTEGER),
            ColumnDef(name="name", display_name="Name", type=ColumnType.STRING),
        ]

        rows = [
            ["Engineering", 100000, "Alice"],
            ["Engineering", 95000, "Bob"],
            ["Sales", 80000, "Charlie"],
        ]

        table = TableData(
            columns=columns,
            rows=rows,
            sort_by=[("department", "asc"), ("salary", "desc"), ("name", "asc")],
        )

        assert len(table.sort_by) == 3
        assert table.sort_by[0] == ("department", "asc")
        assert table.sort_by[1] == ("salary", "desc")
        assert table.sort_by[2] == ("name", "asc")

    def test_complete_table_scenario(self):
        """Test complete table usage scenario."""
        # Define schema
        columns = [
            ColumnDef(
                name="task_id",
                display_name="Task ID",
                type=ColumnType.INTEGER,
                sortable=True,
                width=10,
            ),
            ColumnDef(
                name="task_name",
                display_name="Task Name",
                type=ColumnType.STRING,
                sortable=True,
                width=30,
            ),
            ColumnDef(
                name="assigned_to",
                display_name="Assigned To",
                type=ColumnType.STRING,
                sortable=True,
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.ENUM,
                enum_values=["todo", "in_progress", "done"],
                sortable=False,
                filterable=True,
            ),
            ColumnDef(
                name="priority",
                display_name="Priority",
                type=ColumnType.INTEGER,
                sortable=True,
            ),
            ColumnDef(
                name="due_date",
                display_name="Due Date",
                type=ColumnType.DATE,
                sortable=True,
            ),
        ]

        # Create data
        rows = [
            [1, "Setup database", "Alice", "done", 1, "2024-01-15"],
            [2, "Write API", "Bob", "in_progress", 1, "2024-02-01"],
            [3, "Create frontend", "Charlie", "todo", 2, "2024-02-15"],
            [4, "Write tests", "Alice", "in_progress", 3, "2024-02-10"],
        ]

        # Create table with metadata
        table = TableData(
            columns=columns,
            rows=rows,
            title="Project Tasks",
            description="Current task assignments and status",
            sort_by=[("priority", "asc"), ("status", "asc")],
            filters_applied={"status": "in_progress"},
            selected_columns=[
                "task_id",
                "task_name",
                "assigned_to",
                "status",
                "priority",
            ],
            total_count=50,
            returned_count=4,
        )

        # Verify complete structure
        assert len(table.columns) == 6
        assert len(table.rows) == 4
        assert table.title == "Project Tasks"
        assert table.total_count == 50
        assert table.returned_count == 4
