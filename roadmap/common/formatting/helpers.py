"""Formatting helpers - wrapper to avoid circular dependencies.

This module re-exports OutputFormatHandler from cli_helpers to break
the circular dependency between formatting and utils modules.
"""


# Lazy load to avoid circular imports at module initialization
def __getattr__(name):
    """Lazy load OutputFormatHandler and format_output from cli_helpers."""
    if name == "OutputFormatHandler":
        from roadmap.common.cli_helpers import OutputFormatHandler

        return OutputFormatHandler
    elif name == "format_output":
        from roadmap.common.cli_helpers import format_output

        return format_output
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["format_output", "OutputFormatHandler"]  # noqa: F822
