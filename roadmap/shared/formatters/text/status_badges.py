"""Status badge and percentage formatting.

This module re-exports formatting functions from roadmap.common.formatters
to maintain consistency and eliminate duplication.
"""

# Re-export from common to eliminate duplication
from roadmap.common.formatters import (
    format_percentage,
    format_status_badge,
)

__all__ = ["format_status_badge", "format_percentage"]
