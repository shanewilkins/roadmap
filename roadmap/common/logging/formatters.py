"""Log formatters and data scrubbing for structured logging."""

from typing import Any

# Sensitive keys that should be redacted from logs
SENSITIVE_KEYS = {
    "token",
    "password",
    "secret",
    "api_key",
    "auth",
    "credential",
    "github_token",
}


class StructuredFormatter:
    """Custom formatter that includes structured fields from event data.

    This formatter enhances logging to include any extra fields that were
    passed as structured data via structlog. This makes error context
    (error_type, error_message, etc.) visible in console/file output.
    """

    def format(self, record: dict[str, Any]) -> str:
        """Format event dict with structured fields.

        Args:
            record: Event dictionary from structlog

        Returns:
            Formatted log message with structured fields
        """
        # Get the base message
        base_msg = record.get("event", "")

        # Collect extra fields that aren't standard structlog attributes
        standard_attrs = {
            "event",
            "log_level",
            "timestamp",
            "_from_structlog",
            "_record",
            "_logger",
            "_method_name",
            "_fn_module",
            "_fn_name",
            "_fn_lineno",
            "exception",
            "exc_info",
            "stack_info",
        }

        extra_fields = {}
        for key, value in record.items():
            if key not in standard_attrs and not key.startswith("_"):
                extra_fields[key] = value

        # Append extra fields to message if any exist
        if extra_fields:
            # Format structured fields nicely
            field_strs = []
            for key, value in sorted(extra_fields.items()):
                # Truncate very long values
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:200] + "..."
                field_strs.append(f"{key}={value_str}")

            base_msg += " | " + " ".join(field_strs)

        return base_msg


def scrub_sensitive_data(_logger, _method_name, event_dict):
    """Structlog processor to remove sensitive data from logs."""

    def scrub_value(key, value):
        """Recursively scrub sensitive values."""
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            return "***REDACTED***"
        if isinstance(value, dict):
            return {k: scrub_value(k, v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return type(value)(scrub_value(f"item_{i}", v) for i, v in enumerate(value))
        return value

    return {k: scrub_value(k, v) for k, v in event_dict.items()}


def include_structured_fields_in_message(_logger, _method_name, event_dict):
    """Include structured fields (error_type, error_message, etc.) in the log message.

    This processor appends structured fields to the message so they're visible
    in console/file output, not just in the LogRecord attributes.
    """
    # Extract message
    msg = event_dict.get("event", "")

    # Collect non-standard fields (excluding stdlib ones)
    standard_fields = {
        "event",
        "log_level",
        "timestamp",
        "correlation_id",
        "_from_structlog",
    }
    extra_fields = {k: v for k, v in event_dict.items() if k not in standard_fields}

    # Append extra fields to message if any exist
    if extra_fields:
        field_strs = []
        for key in sorted(extra_fields.keys()):
            value = extra_fields[key]
            value_str = str(value)
            # Truncate very long values
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            field_strs.append(f"{key}={value_str}")

        if field_strs:
            event_dict["event"] = msg + " | " + " ".join(field_strs)

    return event_dict
