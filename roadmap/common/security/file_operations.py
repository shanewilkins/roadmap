"""Secure file and directory operations."""

from contextlib import contextmanager
from pathlib import Path

from ..file_utils import ensure_directory_exists
from .exceptions import SecurityError
from .logging import log_security_event


@contextmanager
def create_secure_file(
    path: str | Path, mode: str = "w", permissions: int = 0o600, **kwargs
):
    """Create a file with secure permissions as a context manager.

    Args:
        path: Path to the file to create
        mode: File open mode (default: 'w')
        permissions: File permissions (default: owner read/write only)
        **kwargs: Additional arguments passed to open()

    Yields:
        File object

    Raises:
        SecurityError: If file creation fails or permissions cannot be set
    """
    path = Path(path)

    try:
        # Create parent directories if they don't exist
        ensure_directory_exists(path.parent)

        # Open file with specified mode
        with open(path, mode, **kwargs) as f:
            # Set secure permissions after file is created
            try:
                path.chmod(permissions)
            except (OSError, PermissionError) as e:
                # Log warning but don't fail - permissions might not be changeable
                log_security_event(
                    "permission_warning", {"path": str(path), "error": str(e)}
                )

            log_security_event(
                "file_created", {"path": str(path), "permissions": oct(permissions)}
            )

            yield f

    except Exception as e:
        log_security_event("file_creation_failed", {"path": str(path), "error": str(e)})
        raise SecurityError(f"Failed to create secure file {path}: {e}") from e


def create_secure_directory(path: Path, permissions: int = 0o700) -> None:
    """Create a directory with secure permissions.

    Args:
        path: Path to the directory to create
        permissions: Directory permissions (default: owner only)

    Raises:
        SecurityError: If directory creation fails
    """
    try:
        ensure_directory_exists(path, permissions=permissions)
        # Note: ensure_directory_exists already sets permissions

        log_security_event(
            "directory_created", {"path": str(path), "permissions": oct(permissions)}
        )
    except Exception as e:
        log_security_event(
            "directory_creation_failed", {"path": str(path), "error": str(e)}
        )
        raise SecurityError(f"Failed to create secure directory {path}: {e}") from e


def secure_file_permissions(path: Path, permissions: int = 0o600) -> None:
    """Set secure permissions on an existing file.

    Args:
        path: Path to the file
        permissions: Permissions to set (default: owner read/write only)

    Raises:
        SecurityError: If permission setting fails
    """
    try:
        if not path.exists():
            raise SecurityError(f"File does not exist: {path}")

        path.chmod(permissions)

        log_security_event(
            "permissions_set", {"path": str(path), "permissions": oct(permissions)}
        )
    except Exception as e:
        log_security_event(
            "permission_setting_failed", {"path": str(path), "error": str(e)}
        )
        raise SecurityError(f"Failed to set secure permissions on {path}: {e}") from e
