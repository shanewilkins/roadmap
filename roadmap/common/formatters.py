"""
Output formatting utilities for CLI display.

Legacy re-export module for backward compatibility.
All formatting functions are now located in roadmap.shared.formatters.text.*
This module re-exports them for existing code that imports from here.
"""

# pylint: disable=unused-import,wrong-import-position
from roadmap.shared.formatters.text.basic import (  # noqa: F401
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
from roadmap.shared.formatters.text.display import (  # noqa: F401
    format_display_list,
    format_display_pairs,
)
from roadmap.shared.formatters.text.duration import (  # noqa: F401
    format_count,
    format_duration,
)
from roadmap.shared.formatters.text.operations import (  # noqa: F401
    format_entity_details,
    format_list_items,
    format_operation_failure,
    format_operation_success,
)
from roadmap.shared.formatters.text.status_badges import (  # noqa: F401
    format_percentage,
    format_status_badge,
)
