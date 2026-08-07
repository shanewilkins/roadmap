"""Formatting helpers - wrapper to avoid circular dependencies.

This module re-exports OutputFormatHandler from cli_helpers to break
the circular dependency between formatting and utils modules.
"""

from typing import TYPE_CHECKING

# Import only for type checking to avoid circular imports
if TYPE_CHECKING:
    from roadmap.common.utils.cli_helpers import OutputFormatHandler, format_output


def __getattr__(name: str):  # noqa: ANN001, ANN201
    """Lazy load OutputFormatHandler and format_output from cli_helpers."""
    if name == "OutputFormatHandler":
        from roadmap.common.utils.cli_helpers import OutputFormatHandler

        return OutputFormatHandler
    elif name == "format_output":
        from roadmap.common.utils.cli_helpers import format_output

        return format_output
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = ["format_output", "OutputFormatHandler"]
