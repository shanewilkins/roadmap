"""Text module public API."""

from .basic import (
    _format_table_simple,
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
from .display import format_display_list, format_display_pairs
from .duration import format_count, format_duration
from .operations import (
    OperationFormatter,
    format_entity_details,
    format_list_items,
    format_operation_failure,
    format_operation_success,
)
from .status_badges import format_percentage, format_status_badge

__all__ = [
    # Basic formatting
    "format_table",
    "format_panel",
    "format_header",
    "format_success",
    "format_error",
    "format_warning",
    "format_info",
    "format_list",
    "format_key_value_pairs",
    "format_json",
    "truncate_text",
    "_format_table_simple",
    # Status and badges
    "format_status_badge",
    "format_percentage",
    # Duration and counts
    "format_duration",
    "format_count",
    # Operations
    "OperationFormatter",
    "format_operation_success",
    "format_operation_failure",
    "format_entity_details",
    "format_list_items",
    # Display
    "format_display_list",
    "format_display_pairs",
]
