"""Secure temporary file utilities."""

import os
import tempfile
from pathlib import Path

from .exceptions import SecurityError
from .logging import log_security_event


def create_secure_temp_file(prefix: str = "roadmap_", suffix: str = ".tmp") -> Path:
    """Create a secure temporary file.

    Args:
        prefix: Prefix for temporary filename
        suffix: Suffix for temporary filename

    Returns:
        Path to the secure temporary file

    Raises:
        SecurityError: If temporary file creation fails
    """
    try:
        # Create secure temporary file
        fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        os.close(fd)  # Close the file descriptor

        # Convert to Path object
        temp_file = Path(temp_path)

        # Set secure permissions (owner read/write only)
        temp_file.chmod(0o600)

        log_security_event("temp_file_created", {"path": str(temp_file)})

        return temp_file

    except Exception as e:
        log_security_event("temp_file_creation_failed", {"error": str(e)})
        raise SecurityError(f"Failed to create secure temporary file: {e}") from e
