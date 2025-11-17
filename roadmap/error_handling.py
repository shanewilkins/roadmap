"""
Unified Error Handling Framework for Roadmap CLI

This module provides centralized error handling utilities, standardized exception classes,
and consistent error reporting mechanisms to eliminate duplicate error handling patterns
across the codebase.

Key Features:
- Custom exception hierarchy for different error types
- Standardized error logging and reporting
- Context managers for consistent error handling
- Error recovery patterns and utilities
- Centralized error message formatting
"""

import logging
import sys
import traceback
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Initialize console for consistent error display
console = Console(stderr=True)

# Configure module logger
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for consistent classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    WARNING = "warning"
    INFO = "info"


class ErrorCategory(Enum):
    """Error categories for better organization and handling."""
    FILE_OPERATION = "file_operation"
    VALIDATION = "validation"
    NETWORK = "network"
    GIT_OPERATION = "git_operation"
    GITHUB_API = "github_api"
    PARSING = "parsing"
    CONFIGURATION = "configuration"
    PERMISSION = "permission"
    DEPENDENCY = "dependency"
    USER_INPUT = "user_input"


# Custom Exception Hierarchy
class RoadmapError(Exception):
    """Base exception for all roadmap-specific errors."""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.VALIDATION,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.cause = cause
        
    def __str__(self) -> str:
        return self.message
    
    def get_context_info(self) -> str:
        """Get formatted context information."""
        if not self.context:
            return ""
        
        context_parts = []
        for key, value in self.context.items():
            context_parts.append(f"{key}: {value}")
        
        return f" ({', '.join(context_parts)})"


class FileOperationError(RoadmapError):
    """Errors related to file operations."""
    
    def __init__(self, message: str, file_path: Optional[Path] = None, operation: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if file_path:
            context['file_path'] = str(file_path)
        if operation:
            context['operation'] = operation
        
        super().__init__(
            message,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            category=ErrorCategory.FILE_OPERATION,
            context=context,
            cause=kwargs.get('cause')
        )
        self.file_path = file_path
        self.operation = operation


class ValidationError(RoadmapError):
    """Errors related to data validation."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        context = kwargs.get('context', {})
        if field:
            context['field'] = field
        if value is not None:
            context['value'] = str(value)
        
        super().__init__(
            message,
            severity=kwargs.get('severity', ErrorSeverity.MEDIUM),
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=kwargs.get('cause')
        )
        self.field = field
        self.value = value


class NetworkError(RoadmapError):
    """Errors related to network operations."""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        context = kwargs.get('context', {})
        if url:
            context['url'] = url
        if status_code:
            context['status_code'] = status_code
        
        super().__init__(
            message,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            category=ErrorCategory.NETWORK,
            context=context,
            cause=kwargs.get('cause')
        )
        self.url = url
        self.status_code = status_code


class GitOperationError(RoadmapError):
    """Errors related to Git operations."""
    
    def __init__(self, message: str, command: Optional[str] = None, exit_code: Optional[int] = None, **kwargs):
        context = kwargs.get('context', {})
        if command:
            context['command'] = command
        if exit_code is not None:
            context['exit_code'] = exit_code
        
        super().__init__(
            message,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            category=ErrorCategory.GIT_OPERATION,
            context=context,
            cause=kwargs.get('cause')
        )
        self.command = command
        self.exit_code = exit_code


class ConfigurationError(RoadmapError):
    """Errors related to configuration."""
    
    def __init__(self, message: str, config_file: Optional[Path] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_file:
            context['config_file'] = str(config_file)
        
        super().__init__(
            message,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            category=ErrorCategory.CONFIGURATION,
            context=context,
            cause=kwargs.get('cause')
        )
        self.config_file = config_file


# Error Handler Class
class ErrorHandler:
    """Centralized error handling utilities."""
    
    def __init__(self, logger: Optional[logging.Logger] = None, console: Optional[Console] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.console = console or Console(stderr=True)
        self.error_counts: Dict[ErrorCategory, int] = {}
    
    def handle_error(
        self,
        error: Union[Exception, RoadmapError],
        context: Optional[Dict[str, Any]] = None,
        show_traceback: bool = False,
        exit_on_critical: bool = True
    ) -> bool:
        """Handle an error with consistent logging and display.
        
        Args:
            error: The error to handle
            context: Additional context information
            show_traceback: Whether to show full traceback
            exit_on_critical: Whether to exit on critical errors
            
        Returns:
            bool: True if error was handled successfully, False if should propagate
        """
        # Convert to RoadmapError if needed
        if not isinstance(error, RoadmapError):
            error = RoadmapError(
                str(error),
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.VALIDATION,
                context=context,
                cause=error
            )
        
        # Update error counts
        self.error_counts[error.category] = self.error_counts.get(error.category, 0) + 1
        
        # Log the error
        self._log_error(error, show_traceback)
        
        # Display to user
        self._display_error(error, show_traceback)
        
        # Handle critical errors
        if error.severity == ErrorSeverity.CRITICAL and exit_on_critical:
            sys.exit(1)
        
        return True
    
    def _log_error(self, error: RoadmapError, show_traceback: bool = False):
        """Log error with appropriate level."""
        log_message = f"{error.category.value}: {error.message}{error.get_context_info()}"
        
        if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            self.logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log traceback if requested or for critical errors
        if show_traceback or error.severity == ErrorSeverity.CRITICAL:
            if error.cause:
                self.logger.error("Caused by:", exc_info=error.cause)
            else:
                self.logger.error("Traceback:", exc_info=True)
    
    def _display_error(self, error: RoadmapError, show_traceback: bool = False):
        """Display error to user with rich formatting."""
        # Choose color based on severity
        color_map = {
            ErrorSeverity.CRITICAL: "red",
            ErrorSeverity.HIGH: "red",
            ErrorSeverity.MEDIUM: "yellow",
            ErrorSeverity.LOW: "blue",
            ErrorSeverity.WARNING: "yellow",
            ErrorSeverity.INFO: "blue"
        }
        
        color = color_map.get(error.severity, "white")
        
        # Create error message
        title = f"{error.severity.value.upper()}: {error.category.value.replace('_', ' ').title()}"
        message = error.message
        
        if error.context:
            context_info = error.get_context_info()
            message += f"\n[dim]{context_info}[/dim]"
        
        if show_traceback and error.cause:
            message += f"\n\n[dim]Caused by: {str(error.cause)}[/dim]"
        
        # Display panel
        panel = Panel(
            message,
            title=title,
            border_style=color,
            expand=False
        )
        
        self.console.print(panel)
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of error counts by category."""
        return dict(self.error_counts)


# Context Manager for Error Handling
@contextmanager
def handle_errors(
    error_handler: Optional[ErrorHandler] = None,
    ignore_errors: bool = False,
    show_traceback: bool = False,
    exit_on_critical: bool = True,
    context: Optional[Dict[str, Any]] = None
):
    """Context manager for consistent error handling.
    
    Args:
        error_handler: Custom error handler instance
        ignore_errors: Whether to suppress all errors
        show_traceback: Whether to show tracebacks
        exit_on_critical: Whether to exit on critical errors
        context: Additional context for errors
    """
    handler = error_handler or ErrorHandler()
    
    try:
        yield handler
    except RoadmapError as e:
        if not ignore_errors:
            handler.handle_error(e, context, show_traceback, exit_on_critical)
        if not ignore_errors and e.severity == ErrorSeverity.CRITICAL:
            raise
    except Exception as e:
        if not ignore_errors:
            roadmap_error = RoadmapError(
                str(e),
                severity=ErrorSeverity.HIGH,
                context=context,
                cause=e
            )
            handler.handle_error(roadmap_error, context, show_traceback, exit_on_critical)
        if not ignore_errors:
            raise


# Decorator for Function Error Handling
def with_error_handling(
    category: ErrorCategory = ErrorCategory.VALIDATION,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ignore_errors: bool = False,
    show_traceback: bool = False,
    default_return: Any = None
):
    """Decorator for adding consistent error handling to functions.
    
    Args:
        category: Error category for classification
        severity: Default error severity
        ignore_errors: Whether to suppress errors and return default
        show_traceback: Whether to show tracebacks
        default_return: Value to return on error (if ignore_errors=True)
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RoadmapError as e:
                if ignore_errors:
                    ErrorHandler().handle_error(e, show_traceback=show_traceback, exit_on_critical=False)
                    return default_return
                raise
            except Exception as e:
                roadmap_error = RoadmapError(
                    f"Error in {func.__name__}: {str(e)}",
                    severity=severity,
                    category=category,
                    cause=e
                )
                if ignore_errors:
                    ErrorHandler().handle_error(roadmap_error, show_traceback=show_traceback, exit_on_critical=False)
                    return default_return
                raise roadmap_error
        
        return wrapper
    return decorator


# Utility Functions
def safe_file_operation(
    operation: Callable,
    file_path: Path,
    operation_name: str,
    default_return: Any = None,
    **kwargs
) -> Any:
    """Safely perform file operations with consistent error handling.
    
    Args:
        operation: Function to execute
        file_path: Path being operated on
        operation_name: Description of operation for error messages
        default_return: Value to return on error
        **kwargs: Additional arguments for operation
    """
    try:
        return operation(**kwargs)
    except FileNotFoundError as e:
        raise FileOperationError(
            f"File not found during {operation_name}",
            file_path=file_path,
            operation=operation_name,
            cause=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied during {operation_name}",
            file_path=file_path,
            operation=operation_name,
            severity=ErrorSeverity.HIGH,
            cause=e
        )
    except OSError as e:
        raise FileOperationError(
            f"OS error during {operation_name}: {str(e)}",
            file_path=file_path,
            operation=operation_name,
            severity=ErrorSeverity.HIGH,
            cause=e
        )


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str],
    context: Optional[str] = None
):
    """Validate that required fields are present in data.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        context: Context description for error messages
        
    Raises:
        ValidationError: If required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        context_msg = f" in {context}" if context else ""
        raise ValidationError(
            f"Missing required fields{context_msg}: {', '.join(missing_fields)}",
            context={'missing_fields': missing_fields, 'context': context}
        )


# Global error handler instance
default_error_handler = ErrorHandler()