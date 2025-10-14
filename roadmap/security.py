"""Security utilities for roadmap CLI application."""

import logging
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Security logger
security_logger = logging.getLogger("roadmap.security")


class SecurityError(Exception):
    """Base exception for security-related errors."""

    pass


class PathValidationError(SecurityError):
    """Exception raised for path validation failures."""

    pass


@contextmanager
def create_secure_file(
    path: Union[str, Path], mode: str = "w", permissions: int = 0o600, **kwargs
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
        path.parent.mkdir(parents=True, exist_ok=True)

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
        raise SecurityError(f"Failed to create secure file {path}: {e}")


def create_secure_directory(path: Path, permissions: int = 0o700) -> None:
    """Create a directory with secure permissions.

    Args:
        path: Path to the directory to create
        permissions: Directory permissions (default: owner only)

    Raises:
        SecurityError: If directory creation fails
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(permissions)

        log_security_event(
            "directory_created", {"path": str(path), "permissions": oct(permissions)}
        )

    except Exception as e:
        log_security_event(
            "directory_creation_failed", {"path": str(path), "error": str(e)}
        )
        raise SecurityError(f"Failed to create secure directory {path}: {e}")


def validate_path(
    path: Union[str, Path],
    base_dir: Optional[Union[str, Path]] = None,
    allow_absolute: bool = False,
) -> Path:
    """Validate that a path is safe and within allowed boundaries.

    Args:
        path: Path to validate
        base_dir: Base directory that path must be within (optional)
        allow_absolute: Whether to allow absolute paths

    Returns:
        Resolved safe path

    Raises:
        PathValidationError: If path is unsafe or outside boundaries
    """
    try:
        # Convert to Path object if string
        if isinstance(path, str):
            path = Path(path)

        # If no base directory specified, just check for basic safety
        if base_dir is None:
            # Still check for directory traversal patterns
            path_str = str(path)
            if ".." in path_str and not allow_absolute:
                raise PathValidationError(
                    f"Path contains potential directory traversal: {path}"
                )

            try:
                return path.resolve()
            except (FileNotFoundError, OSError):
                # If resolve() fails due to missing current directory, handle gracefully
                if path.is_absolute():
                    return path
                else:
                    # For relative paths when cwd is missing, return as-is (caller context should handle)
                    return path

        # Convert base_dir to Path if needed
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)

                # Resolve the path to handle symlinks and .. references
        try:
            resolved_path = path.resolve()
        except (FileNotFoundError, OSError):
            # If resolve fails, work with absolute version or relative to base
            if path.is_absolute():
                resolved_path = path
            else:
                resolved_path = base_dir / path
        
        try:
            resolved_base = base_dir.resolve()
        except (FileNotFoundError, OSError):
            resolved_base = base_dir

        # Check if absolute paths are allowed
        if not allow_absolute and path.is_absolute():
            raise PathValidationError(f"Absolute paths not allowed: {path}")

        # Ensure the resolved path is within the base directory
        try:
            resolved_path.relative_to(resolved_base)
        except ValueError:
            raise PathValidationError(f"Path outside allowed directory: {path}")

        # Check for dangerous path components
        path_parts = resolved_path.parts
        dangerous_parts = {"..", ".", "~"}
        if any(part in dangerous_parts for part in path_parts):
            raise PathValidationError(f"Path contains dangerous components: {path}")

        log_security_event(
            "path_validated",
            {
                "path": str(path),
                "resolved_path": str(resolved_path),
                "base_dir": str(base_dir) if base_dir else None,
            },
        )

        return resolved_path

    except Exception as e:
        log_security_event(
            "path_validation_failed",
            {"path": str(path), "base_dir": str(base_dir), "error": str(e)},
        )
        raise


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
        raise SecurityError(f"Failed to create secure temporary file: {e}")


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
        raise SecurityError(f"Failed to set secure permissions on {path}: {e}")


def log_security_event(event_type: str, details: Dict[str, Any] = None) -> None:
    """Log a security event with structured data.

    Args:
        event_type: Type of security event
        details: Additional event details
    """
    if details is None:
        details = {}

    try:
        # Add timestamp and event type to details
        log_data = {
            "event_type": event_type,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            **details,
        }

        # Only log if the logger has handlers and they're not closed
        if security_logger.handlers:
            # Check if handlers are still valid
            for handler in security_logger.handlers:
                if hasattr(handler, 'stream') and hasattr(handler.stream, 'closed'):
                    if handler.stream.closed:
                        return  # Skip logging if stream is closed
                        
        # Log as structured data
        security_logger.info(f"Security event: {event_type}", extra=log_data)

    except Exception:
        # Don't let logging failures break functionality
        pass


def configure_security_logging(
    log_level: str = "INFO", log_file: Optional[Path] = None
) -> None:
    """Configure security event logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file to log to (in addition to console)
    """
    # Set up security logger
    security_logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    security_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        security_logger.addHandler(file_handler)

        # Secure the log file
        secure_file_permissions(log_file, 0o600)


def validate_export_size(file_path: Path, max_size_mb: int = 100) -> None:
    """Validate that an export file isn't too large.

    Args:
        file_path: Path to the export file
        max_size_mb: Maximum allowed size in MB

    Raises:
        SecurityError: If file is too large
    """
    if not file_path.exists():
        return

    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    if file_size_mb > max_size_mb:
        log_security_event(
            "large_export_detected",
            {
                "path": str(file_path),
                "size_mb": file_size_mb,
                "max_size_mb": max_size_mb,
            },
        )
        raise SecurityError(
            f"Export file too large: {file_size_mb:.1f}MB > {max_size_mb}MB"
        )


def cleanup_old_backups(backup_dir: Path, retention_days: int = 30) -> int:
    """Clean up old backup files for security.

    Args:
        backup_dir: Directory containing backup files
        retention_days: Number of days to retain backups

    Returns:
        Number of files cleaned up
    """
    if not backup_dir.exists():
        return 0

    import time

    cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
    cleaned_count = 0

    try:
        for backup_file in backup_dir.glob("*.backup*"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                cleaned_count += 1

                log_security_event(
                    "backup_cleaned",
                    {
                        "path": str(backup_file),
                        "age_days": (time.time() - backup_file.stat().st_mtime)
                        / (24 * 60 * 60),
                    },
                )

        if cleaned_count > 0:
            log_security_event(
                "backup_cleanup_completed",
                {"files_cleaned": cleaned_count, "retention_days": retention_days},
            )

    except Exception as e:
        log_security_event("backup_cleanup_failed", {"error": str(e)})

    return cleaned_count
