"""File and I/O related error classes."""

from pathlib import Path

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError


class FileOperationError(RoadmapError):
    """Errors related to file operations."""

    def __init__(
        self,
        message: str,
        file_path: Path | None = None,
        operation: str | None = None,
        **kwargs,
    ):
        """Initialize FileOperationError.

        Args:
            message: Error message.
            file_path: Path to the file involved in the error.
            operation: Name of the file operation that failed.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if file_path:
            context["file_path"] = str(file_path)
        if operation:
            context["operation"] = operation

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.FILE_OPERATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.file_path = file_path
        self.operation = operation


class PersistenceError(FileOperationError):
    """Raised when database or file persistence operations fail."""

    pass


class FileLockError(FileOperationError):
    """Raised when file locking operations fail."""

    pass


class DirectoryCreationError(FileOperationError):
    """Raised when directory creation fails."""

    pass


class FileReadError(FileOperationError):
    """Raised when file reading fails."""

    pass


class FileWriteError(FileOperationError):
    """Raised when file writing fails."""

    pass


class ExportError(FileOperationError):
    """Raised when data export fails."""

    pass


class ImportError(FileOperationError):
    """Raised when data import fails."""

    pass
