"""
Click command decorators for structured output with filtering/sorting.

Provides @with_output_support decorator that adds:
- --format flag (rich, plain, json, csv, markdown)
- --columns flag (select columns)
- --sort-by flag (sort results)
- --filter flag (filter results)

Usage:
    @click.command()
    @with_output_support(
        available_columns=["id", "name", "status"],
        column_types={"id": ColumnType.INTEGER, "status": ColumnType.ENUM, ...}
    )
    def list_issues(format, columns, sort_by, filter):
        # Command logic returns TableData
        return TableData(...)
"""

from collections.abc import Callable
from functools import wraps

import click

from roadmap.common.cli_helpers import (
    ColumnSelector,
    FilterSpecParser,
    OutputFormatHandler,
    SortSpecParser,
)
from roadmap.common.console import get_console
from roadmap.common.output_formatter import OutputFormatter
from roadmap.common.output_models import ColumnType, TableData


def with_output_support(
    available_columns: list[str] | None = None,
    column_types: dict[str, ColumnType] | None = None,
    default_columns: list[str] | None = None,
):
    """
    Decorator to add output formatting support to Click commands.

    Adds three flags to command:
    - --format: Output format (rich, plain, json, csv, markdown)
    - --columns: Columns to display (comma-separated)
    - --sort-by: Sort specification (format: col:asc,col2:desc)
    - --filter: Filter specification (format: col=value,col2>=5)

    Args:
        available_columns: List of valid column names for selection.
        column_types: Dict mapping column names to ColumnType for filter validation.
        default_columns: Default columns to show (None = all).

    Example:
        @click.command()
        @with_output_support(
            available_columns=["id", "title", "status", "created"],
            column_types={
                "id": ColumnType.INTEGER,
                "status": ColumnType.ENUM,
                "created": ColumnType.DATETIME,
            }
        )
        def list_issues(format, columns, sort_by, filter):
            issues = issue_service.list_all()
            table = build_table_from_issues(issues)
            return table

    Returns:
        Decorator function.
    """
    available_columns = available_columns or []
    column_types = column_types or {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(
            *args, format=None, columns=None, sort_by=None, filter_spec=None, **kwargs
        ):
            # Call original command with all non-format-related params
            result = func(*args, **kwargs)

            # If result is TableData, apply formatting/filtering/sorting
            if isinstance(result, TableData):
                # Parse and apply column selection
                if columns:
                    selected_cols = ColumnSelector.parse(columns, available_columns)
                    if selected_cols:
                        result = result.select_columns(selected_cols)

                # Parse and apply sorting
                if sort_by:
                    sort_spec = SortSpecParser.parse(sort_by, available_columns)
                    if sort_spec:
                        result = result.sort(sort_spec)

                # Parse and apply filtering
                if filter_spec and column_types:
                    filters = FilterSpecParser.parse(filter_spec, column_types)
                    if filters:
                        for filt in filters:
                            # Simple equality filtering for now
                            # TODO: Add support for other operators (!=, <, >, etc)
                            if filt.operator == "=":
                                result = result.filter(filt.column, filt.value)

                # Render in requested format
                if format and format.lower() != "rich":
                    output = OutputFormatHandler.render(result, format.lower())
                    console = get_console()
                    console.print(output)
                    return  # Don't return TableData, output already printed
                elif format and format.lower() == "rich":
                    # Render as Rich Table and print
                    formatter = OutputFormatter(result)
                    console = get_console()
                    console.print(formatter.to_rich())
                    return  # Rich was printed directly
                else:
                    # Default: return TableData (backwards compat)
                    return result

            return result

        # Add Click options (decorators are applied bottom-up)
        wrapper = click.option(
            "--filter",
            "filter_spec",
            help=FilterSpecParser.get_help_text() if column_types else None,
        )(wrapper)

        wrapper = click.option(
            "--sort-by",
            help=SortSpecParser.get_help_text() if available_columns else None,
        )(wrapper)

        wrapper = click.option(
            "--columns",
            help=ColumnSelector.get_help_text(available_columns)
            if available_columns
            else None,
        )(wrapper)

        wrapper = click.option(
            "--format",
            type=click.Choice(
                ["rich", "plain", "json", "csv", "markdown"], case_sensitive=False
            ),
            default="rich",
            help="Output format (rich=default, plain=POSIX, json=machine-readable, csv=analysis)",
        )(wrapper)

        return wrapper

    return decorator


def add_output_flags(
    available_columns: list[str] | None = None,
    column_types: dict[str, ColumnType] | None = None,
) -> Callable:
    """
    Simpler decorator that just adds flags without automatic processing.

    Use this if you want manual control over how formatting is applied.
    The flags are added to the command, and you handle them manually.

    Example:
        @click.command()
        @add_output_flags(available_columns=["id", "name"])
        def my_command(format, columns, sort_by, filter):
            # You handle the flags manually
            ...

    Returns:
        Decorator function.
    """
    available_columns = available_columns or []
    column_types = column_types or {}

    def decorator(func: Callable) -> Callable:
        func = click.option(
            "--format",
            type=click.Choice(
                ["rich", "plain", "json", "csv", "markdown"], case_sensitive=False
            ),
            default="rich",
            help="Output format",
        )(func)

        func = click.option(
            "--columns",
            help=ColumnSelector.get_help_text(available_columns)
            if available_columns
            else None,
        )(func)

        func = click.option(
            "--sort-by",
            help=SortSpecParser.get_help_text() if available_columns else None,
        )(func)

        func = click.option(
            "--filter",
            "filter_spec",
            help=FilterSpecParser.get_help_text() if column_types else None,
        )(func)

        return func

    return decorator
