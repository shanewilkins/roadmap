"""Filename sanitization utilities."""

import os
import re

from .exceptions import SecurityError
from .logging import log_security_event


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize a filename to prevent security issues.

    Args:
        filename: Original filename
        max_length: Maximum allowed filename length

    Returns:
        Sanitized filename
    """
    if not filename:
        raise SecurityError("Filename cannot be empty")

    # Remove or replace dangerous characters
    # Windows: < > : " | ? * \0
    # Unix: \0 /
    # Generally dangerous: .. (relative path)

    # Replace dangerous characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*\0]', "_", filename)

    # Replace relative path attempts
    sanitized = sanitized.replace("..", "_")

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(" .")

    # Truncate to max length
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        if ext:
            max_name_length = max_length - len(ext)
            sanitized = name[:max_name_length] + ext
        else:
            sanitized = sanitized[:max_length]

    # Ensure we still have a valid filename
    if not sanitized or sanitized in {".", ".."}:
        sanitized = "safe_filename"

    log_security_event(
        "filename_sanitized", {"original": filename, "sanitized": sanitized}
    )

    return sanitized
