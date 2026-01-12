"""Log formatters and data scrubbing for structured logging."""

import logging

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


class StructuredFormatter(logging.Formatter):
    """Custom formatter that includes structured fields from LogRecord extras.

    This formatter enhances the standard logging format to include any extra
    fields that were passed as structured data via structlog. This makes
    error context (error_type, error_message, etc.) visible in the console.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured fields.

        Args:
            record: LogRecord to format

        Returns:
            Formatted log message with structured fields
        """
        # Get the base formatted message
        base_msg = super().format(record)

        # Collect extra fields that aren't standard LogRecord attributes
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "asctime",
        }

        extra_fields = {}
        for key, value in record.__dict__.items():
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


def scrub_sensitive_data(logger, _method_name, event_dict):
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


def include_structured_fields_in_message(logger, _method_name, event_dict):
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
