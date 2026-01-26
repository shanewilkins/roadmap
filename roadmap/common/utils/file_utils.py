"""Unified file operations utilities for roadmap CLI application.

This module provides centralized, consistent file operations to eliminate
DRY violations across the codebase. All file operations should use these
utilities to ensure consistent error handling, logging, and behavior.

Classes:
    FileOperationError: Base exception for file operation failures
    SecureFileManager: Context manager for secure file operations

Functions:
    ensure_directory_exists: Safely create directories with proper error handling
    safe_write_file: Write files with atomic operations and backup support
    safe_read_file: Read files with proper error handling and encoding
    file_exists_check: Unified file existence checking with optional validation
    get_file_size: Get file size with error handling
    backup_file: Create backup of existing file before modification
"""

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from structlog import get_logger

# File operations logger
file_logger = get_logger()


class FileOperationError(Exception):
    """Base exception for file operation failures."""

    def __init__(
        self, message: str, path: Path | None = None, operation: str | None = None
    ):
        """Initialize FileOperationError.

        Args:
            message: Error message.
            path: Path involved in the operation.
            operation: Name of the operation that failed.
        """
        super().__init__(message)
        self.path = path
        self.operation = operation
        file_logger.error(
            f"FileOperationError: {message} (path: {path}, operation: {operation})"
        )


class DirectoryCreationError(FileOperationError):
    """Exception raised for directory creation failures."""

    pass


class FileReadError(FileOperationError):
    """Exception raised for file reading failures."""

    pass


class FileWriteError(FileOperationError):
    """Exception raised for file writing failures."""

    pass


@contextmanager
def SecureFileManager(file_path: str | Path, mode: str = "w", **kwargs):
    """Context manager for secure file operations with automatic cleanup.

    Args:
        file_path: Path to the file
        mode: File open mode
        **kwargs: Additional arguments passed to open()

    Yields:
        File object

    Raises:
        FileOperationError: If file operation fails
    """
    file_path = Path(file_path)
    temp_file = None

    try:
        # Ensure parent directory exists
        ensure_directory_exists(file_path.parent)

        # For write operations, use temporary file for atomicity
        if "w" in mode or "a" in mode:
            temp_file = tempfile.NamedTemporaryFile(
                mode=mode, dir=file_path.parent, delete=False, **kwargs
            )
            yield temp_file
            temp_file.close()

            # Atomic move to final location
            shutil.move(temp_file.name, file_path)
            temp_file = None

        else:
            # For read operations, open directly
            with open(file_path, mode, **kwargs) as f:
                yield f

    except Exception as e:
        if temp_file and hasattr(temp_file, "name"):
            try:
                os.unlink(temp_file.name)
            except OSError:
                pass
        raise FileOperationError(
            f"Secure file operation failed: {e}", Path(file_path), mode
        ) from e


def ensure_directory_exists(
    directory_path: str | Path,
    permissions: int = 0o755,
    parents: bool = True,
    exist_ok: bool = True,
) -> Path:
    """Safely create directory with proper error handling and logging.

    This function centralizes all directory creation logic to eliminate
    the repeated pattern: directory.mkdir(parents=True, exist_ok=True)

    Args:
        directory_path: Path to the directory to create
        permissions: Directory permissions (default: 0o755)
        parents: Create parent directories if needed (default: True)
        exist_ok: Don't raise error if directory already exists (default: True)

    Returns:
        Path object of the created directory

    Raises:
        DirectoryCreationError: If directory creation fails
    """
    try:
        directory_path = Path(directory_path)
        directory_path.mkdir(mode=permissions, parents=parents, exist_ok=exist_ok)

        file_logger.debug(
            "directory_ensured",
            directory_path=str(directory_path),
        )
        return directory_path

    except OSError as e:
        raise DirectoryCreationError(
            f"Failed to create directory: {e}", Path(directory_path), "mkdir"
        ) from e


def safe_write_file(
    file_path: str | Path,
    content: str,
    encoding: str = "utf-8",
    backup: bool = False,
    atomic: bool = True,
) -> Path:
    """Write file content safely with atomic operations and optional backup.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        encoding: File encoding (default: utf-8)
        backup: Create backup of existing file (default: False)
        atomic: Use atomic write operation (default: True)

    Returns:
        Path object of the written file

    Raises:
        FileWriteError: If file writing fails
    """
    try:
        file_path = Path(file_path)

        # Ensure parent directory exists
        ensure_directory_exists(file_path.parent)

        # Create backup if requested and file exists
        if backup and file_path.exists():
            backup_file(file_path)

        if atomic:
            # Use atomic write with temporary file
            with SecureFileManager(file_path, "w", encoding=encoding) as f:
                f.write(content)
        else:
            # Direct write
            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)

        file_logger.debug(
            "file_written_safely",
            file_path=str(file_path),
            char_count=len(content),
        )
        return file_path

    except Exception as e:
        raise FileWriteError(
            f"Failed to write file: {e}", Path(file_path), "write"
        ) from e


def safe_read_file(
    file_path: str | Path, encoding: str = "utf-8", default: str | None = None
) -> str:
    """Read file content safely with proper error handling.

    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)
        default: Default content to return if file doesn't exist

    Returns:
        File content as string

    Raises:
        FileReadError: If file reading fails
        FileNotFoundError: If file doesn't exist and no default provided
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            if default is not None:
                file_logger.debug(
                    "file_not_found_returning_default",
                    file_path=str(file_path),
                )
                return default
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding=encoding)
        file_logger.debug(
            "file_read_safely",
            file_path=str(file_path),
            char_count=len(content),
        )
        return content

    except FileNotFoundError:
        raise
    except Exception as e:
        raise FileReadError(f"Failed to read file: {e}", Path(file_path), "read") from e


def file_exists_check(
    file_path: str | Path,
    must_be_file: bool = True,
    must_be_readable: bool = False,
    min_size: int | None = None,
) -> bool:
    """Unified file existence checking with optional validation.

    This function centralizes all file existence checks to eliminate
    the repeated patterns: if file.exists() or if not file.exists()

    Args:
        file_path: Path to check
        must_be_file: Ensure path is a file, not directory (default: True)
        must_be_readable: Ensure file is readable (default: False)
        min_size: Minimum file size in bytes (default: None)

    Returns:
        True if file exists and meets all criteria, False otherwise
    """
    try:
        file_path = Path(file_path)

        # Basic existence check
        if not file_path.exists():
            return False

        # Check if it's actually a file
        if must_be_file and not file_path.is_file():
            return False

        # Check if file is readable
        if must_be_readable and not os.access(file_path, os.R_OK):
            return False

        # Check minimum size
        if min_size is not None:
            if file_path.stat().st_size < min_size:
                return False

        return True

    except Exception as e:
        file_logger.warning(
            "file_existence_check_failed",
            file_path=str(file_path),
            error=str(e),
            severity="operational",
        )
        return False


def get_file_size(file_path: str | Path) -> int:
    """Get file size with error handling.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes

    Raises:
        FileOperationError: If unable to get file size
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        size = file_path.stat().st_size
        file_logger.debug(
            "file_size_retrieved",
            file_path=str(file_path),
            size_bytes=size,
        )
        return size

    except Exception as e:
        raise FileOperationError(
            f"Failed to get file size: {e}", Path(file_path), "stat"
        ) from e


def backup_file(
    file_path: str | Path,
    backup_suffix: str = ".backup",
    backup_dir: str | Path | None = None,
) -> Path | None:
    """Create backup of existing file before modification.

    Args:
        file_path: Path to the file to backup
        backup_suffix: Suffix to add to backup file (default: .backup)
        backup_dir: Directory to store backups (default: same as original)

    Returns:
        Path to backup file if created, None if original doesn't exist

    Raises:
        FileOperationError: If backup creation fails
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        if backup_dir:
            backup_dir = Path(backup_dir)
            ensure_directory_exists(backup_dir)
            backup_path = backup_dir / f"{file_path.name}{backup_suffix}"
        else:
            backup_path = file_path.with_suffix(f"{file_path.suffix}{backup_suffix}")

        shutil.copy2(file_path, backup_path)
        file_logger.info(
            "file_backed_up",
            file_path=str(file_path),
            backup_path=str(backup_path),
        )
        return backup_path

    except Exception as e:
        raise FileOperationError(
            f"Failed to create backup: {e}", Path(file_path), "backup"
        ) from e


def cleanup_temp_files(directory: str | Path, pattern: str = "*.tmp") -> int:
    """Clean up temporary files in a directory.

    Args:
        directory: Directory to clean
        pattern: File pattern to match (default: *.tmp)

    Returns:
        Number of files cleaned up

    Raises:
        FileOperationError: If cleanup fails
    """
    try:
        directory = Path(directory)
        count = 0

        if not directory.exists():
            return 0

        for temp_file in directory.glob(pattern):
            try:
                temp_file.unlink()
                count += 1
                file_logger.debug(
                    "temp_file_cleaned_up",
                    temp_file=str(temp_file),
                )
            except OSError as e:
                file_logger.warning(
                    "failed_to_remove_temp_file",
                    temp_file=str(temp_file),
                    error=str(e),
                    severity="operational",
                )

        if count > 0:
            file_logger.info(
                "temporary_files_cleaned_up",
                count=count,
                directory=str(directory),
            )

        return count

    except Exception as e:
        raise FileOperationError(
            f"Failed to cleanup temp files: {e}",
            Path(directory) if isinstance(directory, str) else directory,
            "cleanup",
        ) from e
