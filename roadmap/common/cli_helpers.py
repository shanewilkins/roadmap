"""
CLI helpers for structured output formatting and filtering.

Provides decorators, utilities, and helpers for commands to support
--format, --columns, and --sort-by flags for consistent user experience.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

import click

from roadmap.common.output_formatter import OutputFormatter
from roadmap.common.output_models import ColumnType, TableData


class OutputFormatHandler:
    """
    Handles output format selection and rendering.

    Supports: rich (default), plain-text, json, csv, markdown
    """

    SUPPORTED_FORMATS = {
        "rich": "Interactive terminal output with colors",
        "plain": "POSIX-safe ASCII tables",
        "json": "Machine-readable JSON format",
        "csv": "Comma-separated values for analysis",
        "markdown": "Markdown tables for documentation",
    }

    @staticmethod
    def render(table_data: TableData, format_name: str = "rich") -> str:
        """
        Render table data in specified format.

        Args:
            table_data: TableData object to render.
            format_name: Output format (rich, plain, json, csv, markdown).

        Returns:
            Formatted string output.

        Raises:
            ValueError: If format_name is not supported.
        """
        if format_name not in OutputFormatHandler.SUPPORTED_FORMATS:
            raise ValueError(f"Unknown format: {format_name}")

        formatter = OutputFormatter(table_data)

        if format_name == "plain":
            return formatter.to_plain_text()
        elif format_name == "json":
            return formatter.to_json()
        elif format_name == "csv":
            return formatter.to_csv()
        elif format_name == "markdown":
            return formatter.to_markdown()
        else:  # rich (default)
            # Rich returns a Table object, needs console.print()
            return formatter.to_rich()


class ColumnSelector:
    """
    Smart column selection utility.

    Handles --columns flag parsing and validation:
    - Comma-separated column names
    - Validates columns exist
    - Respects column order
    - Case-insensitive matching
    """

    @staticmethod
    def parse(
        columns_str: str | None, available_columns: list[str]
    ) -> list[str] | None:
        """
        Parse --columns flag value.

        Args:
            columns_str: Raw --columns value (comma-separated).
            available_columns: List of valid column names.

        Returns:
            Normalized list of column names or None if not specified.

        Raises:
            click.BadParameter: If column name doesn't exist.
        """
        if not columns_str:
            return None

        # Parse comma-separated list
        requested = [col.strip() for col in columns_str.split(",")]

        # Validate all columns exist (case-insensitive)
        column_map = {col.lower(): col for col in available_columns}
        normalized = []

        for col in requested:
            col_lower = col.lower()
            if col_lower not in column_map:
                available_str = ", ".join(available_columns)
                raise click.BadParameter(
                    f"Unknown column: {col}. Available columns: {available_str}"
                )
            normalized.append(column_map[col_lower])

        return normalized

    @staticmethod
    def get_help_text(available_columns: list[str]) -> str:
        """Get help text for --columns flag."""
        cols = ", ".join(available_columns)
        return f"Columns to display (comma-separated). Available: {cols}"


class SortSpecParser:
    """
    Parse and validate --sort-by flag.

    Handles:
    - Single column: --sort-by name
    - Multiple columns: --sort-by name,age
    - Direction: --sort-by name:asc,age:desc
    - Validates columns exist
    - Respects direction (asc/desc, default asc)
    """

    @staticmethod
    def parse(sort_str: str | None, available_columns: list[str]) -> list[tuple] | None:
        """
        Parse --sort-by flag value.

        Args:
            sort_str: Raw --sort-by value (format: col1:asc,col2:desc).
            available_columns: List of valid column names.

        Returns:
            List of (column_name, direction) tuples or None if not specified.

        Raises:
            click.BadParameter: If column name doesn't exist or direction invalid.
        """
        if not sort_str:
            return None

        # Parse comma-separated sort specs
        specs = []
        column_map = {col.lower(): col for col in available_columns}

        for item in sort_str.split(","):
            item = item.strip()

            # Split on colon (column:direction)
            if ":" in item:
                col_name, direction = item.split(":", 1)
                col_name = col_name.strip()
                direction = direction.strip().lower()
            else:
                col_name = item
                direction = "asc"

            # Validate column exists
            col_lower = col_name.lower()
            if col_lower not in column_map:
                available_str = ", ".join(available_columns)
                raise click.BadParameter(
                    f"Unknown sort column: {col_name}. Available: {available_str}"
                )

            # Validate direction
            if direction not in ("asc", "desc"):
                raise click.BadParameter(
                    f"Invalid sort direction '{direction}' for column {col_name}. "
                    "Use 'asc' or 'desc'."
                )

            specs.append((column_map[col_lower], direction))

        return specs if specs else None

    @staticmethod
    def get_help_text() -> str:
        """Get help text for --sort-by flag."""
        return (
            "Sort by columns (format: col1:asc,col2:desc). "
            "Direction defaults to 'asc' if omitted."
        )


class FilterSpec:
    """
    Represents a single filter specification.

    Used internally for parsed --filter arguments.
    """

    def __init__(self, column: str, operator: str, value: Any):
        """
        Initialize filter spec.

        Args:
            column: Column name to filter.
            operator: Comparison operator (=, !=, <, >, <=, >=, ~).
            value: Filter value (type-aware parsing).
        """
        self.column = column
        self.operator = operator
        self.value = value

    def __repr__(self):
        return f"FilterSpec({self.column}{self.operator}{self.value})"


class FilterSpecParser:
    """
    Parse and validate --filter flags.

    Handles:
    - Simple equality: --filter status=open
    - Negation: --filter status!=closed
    - Comparisons: --filter count>=5
    - Regex: --filter title~bug
    - Case-insensitive matching
    - Type-aware value conversion (string, int, bool)
    """

    # Order matters: longer operators first to avoid partial matches
    VALID_OPERATORS = ["!=", "<=", ">=", "=", "~", "<", ">"]

    @staticmethod
    def parse(
        filter_str: str | None, column_types: dict[str, ColumnType]
    ) -> list[FilterSpec] | None:
        """
        Parse --filter flag value(s).

        Args:
            filter_str: Raw --filter value(s).
            column_types: Dict mapping column name to ColumnType.

        Returns:
            List of FilterSpec objects or None if not specified.

        Raises:
            click.BadParameter: If column or operator invalid.
        """
        if not filter_str:
            return None

        specs = []
        column_map = {col.lower(): col for col in column_types.keys()}

        # Parse space-separated filter specs
        for item in filter_str.split(","):
            item = item.strip()
            if not item:
                continue

            # Find operator
            operator = None
            for op in FilterSpecParser.VALID_OPERATORS:
                if op in item:
                    operator = op
                    break

            if not operator:
                raise click.BadParameter(
                    f"Invalid filter syntax: {item}. Use format: column=value"
                )

            col_name, value_str = item.split(operator, 1)
            col_name = col_name.strip()
            value_str = value_str.strip()

            # Validate column exists
            col_lower = col_name.lower()
            if col_lower not in column_map:
                available = ", ".join(column_types.keys())
                raise click.BadParameter(
                    f"Unknown filter column: {col_name}. Available: {available}"
                )

            col_name = column_map[col_lower]
            col_type = column_types[col_name]

            # Parse value with type awareness
            value = FilterSpecParser._parse_value(value_str, col_type)

            specs.append(FilterSpec(col_name, operator, value))

        return specs if specs else None

    @staticmethod
    def _parse_value(value_str: str, col_type: ColumnType) -> Any:
        """Parse filter value with type awareness."""
        if col_type == ColumnType.INTEGER:
            try:
                return int(value_str)
            except ValueError as err:
                raise click.BadParameter(
                    f"Expected integer value, got: {value_str}"
                ) from err

        elif col_type == ColumnType.FLOAT:
            try:
                return float(value_str)
            except ValueError as err:
                raise click.BadParameter(
                    f"Expected float value, got: {value_str}"
                ) from err

        elif col_type == ColumnType.BOOLEAN:
            if value_str.lower() in ("true", "yes", "1", "on"):
                return True
            elif value_str.lower() in ("false", "no", "0", "off"):
                return False
            else:
                raise click.BadParameter(
                    f"Expected boolean value, got: {value_str}. Use: true/false, yes/no"
                )

        else:  # STRING, DATE, DATETIME, ENUM
            return value_str

    @staticmethod
    def get_help_text() -> str:
        """Get help text for --filter flag."""
        return (
            "Filter rows (format: column=value). "
            "Operators: = != < > <= >= ~ (regex). "
            "Example: --filter status=open --filter count>=5"
        )


def format_output(
    format_choice: str = "rich", columns: list[str] | None = None
) -> Callable:
    """
    Decorator to handle output formatting.

    Wraps command functions to:
    1. Convert returned TableData to formatted output
    2. Apply column selection
    3. Render in specified format

    Usage:
        @click.command()
        @click.option("--format", type=click.Choice(["rich", "plain", "json", "csv"]))
        @click.option("--columns", help="Columns to display")
        @format_output()
        def my_command(format, columns, ...):
            return TableData(...)

    Args:
        format_choice: Output format (rich, plain, json, csv, markdown).
        columns: Column names to select (None = all).

    Returns:
        Decorator function.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Call original function
            result = func(*args, **kwargs)

            # If result is TableData, format it
            if isinstance(result, TableData):
                # Apply column selection if specified
                if columns:
                    result = result.select_columns(columns)

                # Render in requested format
                if format_choice == "rich":
                    # For rich, return Table object for console.print()
                    return OutputFormatter(result).to_rich()
                else:
                    return OutputFormatHandler.render(result, format_choice)

            return result

        return wrapper

    return decorator
