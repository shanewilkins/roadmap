"""Formatting and output utilities for console display."""

from .helpers import OutputFormatHandler, format_output

__all__ = [
    "OutputFormatHandler",
    "format_output",
]


def __getattr__(name):
    """Lazy load formatting modules to avoid circular dependencies."""
    # Map of names to their module paths
    formatters = {
        "get_console": ("console", "get_console"),
        "get_console_stderr": ("console", "get_console_stderr"),
        "is_plain_mode": ("console", "is_plain_mode"),
        "is_testing_environment": ("console", "is_testing_environment"),
        "format_error_message": ("error_formatter", "format_error_message"),
        "format_info_message": ("error_formatter", "format_info_message"),
        "format_success_message": ("error_formatter", "format_success_message"),
        "format_warning_message": ("error_formatter", "format_warning_message"),
        "CSVOutputFormatter": ("output_formatter", "CSVOutputFormatter"),
        "HTMLOutputFormatter": ("output_formatter", "HTMLOutputFormatter"),
        "JSONOutputFormatter": ("output_formatter", "JSONOutputFormatter"),
        "OutputFormatter": ("output_formatter", "OutputFormatter"),
        "PlainTextOutputFormatter": ("output_formatter", "PlainTextOutputFormatter"),
        "ProgressCalculationEngine": ("progress", "ProgressCalculationEngine"),
        "ProgressEventSystem": ("progress", "ProgressEventSystem"),
        "StatusStyleManager": ("status_style_manager", "StatusStyleManager"),
    }

    if name in formatters:
        module_name, attr_name = formatters[name]
        # Import from parent common module's submodules
        import importlib

        mod = importlib.import_module(f"roadmap.common.{module_name}")
        return getattr(mod, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Console
    "get_console",
    "get_console_stderr",
    "is_plain_mode",
    "is_testing_environment",
    # Error formatting
    "format_error_message",
    "format_info_message",
    "format_success_message",
    "format_warning_message",
    # Output formatters
    "CSVOutputFormatter",
    "HTMLOutputFormatter",
    "JSONOutputFormatter",
    "OutputFormatter",
    "PlainTextOutputFormatter",
    # Helpers
    "OutputFormatHandler",
    "format_output",
    # Progress
    "ProgressCalculationEngine",
    "ProgressEventSystem",
    # Status styling
    "StatusStyleManager",
]
