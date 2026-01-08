"""
Output abstraction layer - Core data structures for structured output.

This module provides the foundation for multi-format output (Rich, plain-text, JSON, CSV).
Commands return structured TableData objects instead of formatted strings, allowing
the same data to be rendered in multiple formats.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ColumnType(str, Enum):
    """Supported column data types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"


@dataclass
class ColumnDef:
    """
    Metadata for a single table column.

    This separates column structure from presentation, enabling the same
    column to be rendered in multiple output formats.

    Attributes:
        name: Column identifier (e.g., "id", "title"). Used for filtering/sorting.
        display_name: Human-readable header (e.g., "ID", "Title").
        type: Column data type (string, integer, date, enum, etc.).
        width: Suggested display width in characters (for text-based formats).
        headline: Help text describing the column purpose.
        display_style: Rich styling (e.g., "cyan", "bold green"). Ignored in plain-text/JSON/CSV.
        enum_values: Valid values for type="enum". None for other types.
        sortable: Can users sort by this column?
        filterable: Can users filter by this column?

    Example:
        ColumnDef(
            name="status",
            display_name="Status",
            type=ColumnType.ENUM,
            width=10,
            headline="Issue status",
            display_style="yellow",
            enum_values=["open", "closed", "blocked"],
            sortable=True,
            filterable=True,
        )
    """

    name: str
    display_name: str
    type: ColumnType = ColumnType.STRING
    width: int | None = None
    headline: str = ""
    display_style: str | None = None
    enum_values: list[str] | None = None
    sortable: bool = True
    filterable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Export column metadata as dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "type": self.type.value,
            "width": self.width,
            "headline": self.headline,
            "display_style": self.display_style,
            "enum_values": self.enum_values,
            "sortable": self.sortable,
            "filterable": self.filterable,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ColumnDef":
        """Import column metadata from dictionary."""
        return ColumnDef(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            type=ColumnType(data.get("type", "string")),
            width=data.get("width"),
            headline=data.get("headline", ""),
            display_style=data.get("display_style"),
            enum_values=data.get("enum_values"),
            sortable=data.get("sortable", True),
            filterable=data.get("filterable", True),
        )


@dataclass
class TableData:
    """
    Structured table data with metadata.

    Contains the data and metadata needed to render a table in any format
    (Rich, plain-text, JSON, CSV). This decouples data from presentation.

    Attributes:
        columns: List of ColumnDef objects defining table structure.
        rows: List of rows, where each row is a list of values matching column order.
        title: Optional table title/heading.
        headline: Optional table description.
        filters_applied: Dictionary of {column_name: filter_value} for active filters.
        sort_by: List of (column_name, "asc"|"desc") tuples for sort order.
        selected_columns: List of column names to display (None = all columns).
        total_count: Total number of rows before filtering (for pagination).
        returned_count: Number of rows returned after filtering.

    Example:
        table = TableData(
            columns=[
                ColumnDef(name="id", display_name="ID", type=ColumnType.STRING, width=9),
                ColumnDef(name="title", display_name="Title", type=ColumnType.STRING),
                ColumnDef(name="status", display_name="Status", type=ColumnType.ENUM,
                         enum_values=["open", "closed"]),
            ],
            rows=[
                ["123", "Fix bug", "open"],
                ["124", "Add feature", "closed"],
            ],
            title="Issues",
        )
    """

    columns: list[ColumnDef]
    rows: list[list[Any]]
    title: str | None = None
    headline: str | None = None
    filters_applied: dict[str, Any] = field(default_factory=dict)
    sort_by: list[tuple[str, str]] | list = field(default_factory=list)
    selected_columns: list[str] | None = None
    total_count: int | None = None
    returned_count: int | None = None

    def __post_init__(self):
        """Validate table structure after initialization."""
        # Validate row structure
        if self.rows:
            expected_columns = len(self.columns)
            for i, row in enumerate(self.rows):
                if len(row) != expected_columns:
                    raise ValueError(
                        f"Row {i} has {len(row)} values but {expected_columns} columns expected"
                    )

        # Set defaults for counts
        if self.total_count is None:
            self.total_count = len(self.rows)
        if self.returned_count is None:
            self.returned_count = len(self.rows)

    @property
    def active_columns(self) -> list[ColumnDef]:
        """Get columns to display (respecting selected_columns)."""
        if self.selected_columns:
            # Return columns in selected order
            col_map = {col.name: col for col in self.columns}
            return [col_map[name] for name in self.selected_columns if name in col_map]
        return self.columns

    @property
    def active_rows(self) -> list[list[Any]]:
        """Get rows with only selected columns."""
        if not self.selected_columns:
            return self.rows

        # Build column index mapping
        col_indices = {col.name: i for i, col in enumerate(self.columns)}
        selected_indices = [
            col_indices[name] for name in self.selected_columns if name in col_indices
        ]

        # Filter row values
        return [[row[i] for i in selected_indices] for row in self.rows]

    def filter(self, column: str, value: Any) -> "TableData":
        """
        Apply filter and return new TableData.

        Args:
            column: Column name to filter by.
            value: Value(s) to filter for. Can be single value or list for IN filter.

        Returns:
            New TableData with filtered rows.

        Raises:
            ValueError: If column doesn't exist or value doesn't match enum values.
        """
        # Validate column exists
        col = next((c for c in self.columns if c.name == column), None)
        if not col:
            raise ValueError(f"Column '{column}' not found")
        if not col.filterable:
            raise ValueError(f"Column '{column}' is not filterable")

        # Validate enum values if applicable
        if col.type == ColumnType.ENUM and col.enum_values:
            values_to_check = value if isinstance(value, list) else [value]
            for v in values_to_check:
                if v not in col.enum_values:
                    raise ValueError(f"Invalid value '{v}' for enum column '{column}'")

        # Find column index
        col_index = next(i for i, c in enumerate(self.columns) if c.name == column)

        # Filter rows
        if isinstance(value, list):
            # IN filter
            filtered_rows = [row for row in self.rows if row[col_index] in value]
        else:
            # Equality filter
            filtered_rows = [row for row in self.rows if row[col_index] == value]

        # Create new TableData with updated state
        new_table = TableData(
            columns=self.columns,
            rows=filtered_rows,
            title=self.title,
            headline=self.headline,
            filters_applied={**self.filters_applied, column: value},
            sort_by=self.sort_by,
            selected_columns=self.selected_columns,
            total_count=self.total_count,
            returned_count=len(filtered_rows),
        )
        return new_table

    def sort(self, sort_spec: str | list[tuple[str, str]]) -> "TableData":
        """
        Apply sorting and return new TableData.

        Args:
            sort_spec: Either a string (column name, ascending) or
                      list of (column_name, "asc"|"desc") tuples.
                      Sorts by first column, then second, etc.

        Returns:
            New TableData with sorted rows.

        Raises:
            ValueError: If column doesn't exist or is not sortable.
        """
        # Normalize sort_spec to list of tuples
        if isinstance(sort_spec, str):
            sort_spec_list = [(sort_spec, "asc")]
        else:
            sort_spec_list = sort_spec

        # Validate columns and build sort key function
        col_indices = {}
        sort_directions = {}

        for col_name, direction in sort_spec_list:
            col = next((c for c in self.columns if c.name == col_name), None)
            if not col:
                raise ValueError(f"Column '{col_name}' not found")
            if not col.sortable:
                raise ValueError(f"Column '{col_name}' is not sortable")

            col_index = next(
                i for i, c in enumerate(self.columns) if c.name == col_name
            )
            col_indices[col_name] = col_index
            sort_directions[col_name] = direction.lower() == "desc"

        # Sort rows using multiple keys
        def sort_key(row):
            keys = []
            for col_name, _ in sort_spec_list:
                index = col_indices[col_name]
                value = row[index]
                # Handle None values
                if value is None:
                    keys.append((1, value))  # None sorts to end
                else:
                    keys.append((0, value))
            return tuple(keys)

        sorted_rows = sorted(self.rows, key=sort_key)

        # Apply descending direction
        for col_name, _direction in reversed(sort_spec_list):
            if sort_directions[col_name]:
                sorted_rows.reverse()

        # Create new TableData with updated state
        new_table = TableData(
            columns=self.columns,
            rows=sorted_rows,
            title=self.title,
            headline=self.headline,
            filters_applied=self.filters_applied,
            sort_by=sort_spec_list,
            selected_columns=self.selected_columns,
            total_count=self.total_count,
            returned_count=self.returned_count,
        )
        return new_table

    def select_columns(self, columns: list[str]) -> "TableData":
        """
        Select specific columns to display.

        Args:
            columns: List of column names to display.

        Returns:
            New TableData with column selection applied.

        Raises:
            ValueError: If any column name doesn't exist.
        """
        # Validate all columns exist
        col_names = {c.name for c in self.columns}
        for col in columns:
            if col not in col_names:
                raise ValueError(f"Column '{col}' not found")

        # Create new TableData with column selection
        new_table = TableData(
            columns=self.columns,
            rows=self.rows,
            title=self.title,
            headline=self.headline,
            filters_applied=self.filters_applied,
            sort_by=self.sort_by,
            selected_columns=columns,
            total_count=self.total_count,
            returned_count=self.returned_count,
        )
        return new_table

    def to_dict(self) -> dict[str, Any]:
        """Export table as dictionary (useful for JSON)."""
        return {
            "title": self.title,
            "headline": self.headline,
            "columns": [col.to_dict() for col in self.columns],
            "rows": self.active_rows,
            "metadata": {
                "total": self.total_count,
                "returned": self.returned_count,
                "filters_applied": self.filters_applied,
                "sort_by": self.sort_by,
                "selected_columns": self.selected_columns,
            },
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TableData":
        """Import table from dictionary."""
        return TableData(
            columns=[ColumnDef.from_dict(col) for col in data.get("columns", [])],
            rows=data.get("rows", []),
            title=data.get("title"),
            description=data.get("description"),
            filters_applied=data.get("metadata", {}).get("filters_applied", {}),
            sort_by=data.get("metadata", {}).get("sort_by", []),
            selected_columns=data.get("metadata", {}).get("selected_columns"),
            total_count=data.get("metadata", {}).get("total"),
            returned_count=data.get("metadata", {}).get("returned"),
        )
