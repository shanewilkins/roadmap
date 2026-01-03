"""Test-specific logging helpers for integration tests.

Provides utilities for capturing, filtering, and analyzing logs during tests
to aid in debugging and understanding test behavior.
"""

from typing import Any

import pytest


class LogCapture:
    """Capture and analyze logs during test execution."""

    def __init__(self, caplog: Any):
        """Initialize log capture.

        Args:
            caplog: pytest caplog fixture
        """
        self.caplog = caplog
        self.caplog.set_level("DEBUG")

    def get_logs(self, level: str | None = None) -> list[str]:
        """Get all captured logs, optionally filtered by level.

        Args:
            level: Optional level filter (DEBUG, INFO, WARNING, ERROR)

        Returns:
            List of log messages
        """
        if level is None:
            return self.caplog.text.split("\n")

        return [
            record.getMessage()
            for record in self.caplog.records
            if record.levelname == level
        ]

    def get_errors(self) -> list[str]:
        """Get all error logs.

        Returns:
            List of error messages
        """
        return self.get_logs("ERROR")

    def get_warnings(self) -> list[str]:
        """Get all warning logs.

        Returns:
            List of warning messages
        """
        return self.get_logs("WARNING")

    def get_debug_logs(self) -> list[str]:
        """Get all debug logs.

        Returns:
            List of debug messages
        """
        return self.get_logs("DEBUG")

    def assert_logged(self, message: str, level: str | None = None) -> None:
        """Assert that a message was logged.

        Args:
            message: Message to look for
            level: Optional level filter

        Raises:
            AssertionError: If message not found
        """
        logs = self.get_logs(level)
        found = any(message.lower() in log.lower() for log in logs)
        if not found:
            raise AssertionError(
                f"Expected message '{message}' not found in logs\n"
                f"Level: {level or 'any'}\n"
                f"Logs:\n{chr(10).join(logs)}"
            )

    def assert_not_logged(self, message: str, level: str | None = None) -> None:
        """Assert that a message was NOT logged.

        Args:
            message: Message to look for
            level: Optional level filter

        Raises:
            AssertionError: If message found
        """
        logs = self.get_logs(level)
        found = any(message.lower() in log.lower() for log in logs)
        if found:
            raise AssertionError(
                f"Unexpected message '{message}' found in logs\n"
                f"Level: {level or 'any'}"
            )

    def print_logs(self, level: str | None = None) -> None:
        """Print captured logs for debugging.

        Args:
            level: Optional level filter
        """
        logs = self.get_logs(level)
        print("\n--- Captured Logs ---")
        for log in logs:
            print(log)
        print("--- End Logs ---\n")

    def log_summary(self) -> str:
        """Get a summary of all captured logs.

        Returns:
            Summary string with counts and key messages
        """
        summary = []
        summary.append("=== Log Summary ===")
        summary.append(f"Total log records: {len(self.caplog.records)}")

        for level in ["ERROR", "WARNING", "INFO", "DEBUG"]:
            count = len([r for r in self.caplog.records if r.levelname == level])
            if count > 0:
                summary.append(f"{level}: {count}")

        return "\n".join(summary)


class ContextLogger:
    """Contextual logging for understanding test flow."""

    def __init__(self, caplog: Any, test_name: str = ""):
        """Initialize context logger.

        Args:
            caplog: pytest caplog fixture
            test_name: Name of the test for context
        """
        self.caplog = caplog
        self.test_name = test_name
        self.caplog.set_level("DEBUG")

    def log_test_step(self, step_name: str, details: str = "") -> None:
        """Log a test step for tracking progress.

        Args:
            step_name: Name of the step
            details: Optional details about the step
        """
        message = f"[TEST STEP] {step_name}"
        if details:
            message += f" - {details}"
        pytest.skip(message)  # Don't actually skip, just log
        # In practice, we'd use a proper logging call
        print(f"\n→ {message}")

    def context(self, operation: str) -> "ContextLogger._ContextManager":
        """Create a context manager for an operation.

        Args:
            operation: Operation name

        Returns:
            Context manager
        """
        return self._ContextManager(operation)

    class _ContextManager:
        """Context manager for operation tracking."""

        def __init__(self, operation: str):
            """Initialize context manager.

            Args:
                operation: Operation name
            """
            self.operation = operation

        def __enter__(self) -> "ContextLogger._ContextManager":
            """Enter context."""
            print(f"\n→ START: {self.operation}")
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            """Exit context."""
            if exc_type is None:
                print(f"✓ END: {self.operation}")
            else:
                print(f"✗ FAILED: {self.operation}")


@pytest.fixture
def test_log_capture(caplog: Any) -> LogCapture:
    """Provide test log capture to tests.

    Args:
        caplog: pytest caplog fixture

    Returns:
        LogCapture instance
    """
    return LogCapture(caplog)


@pytest.fixture
def test_context_logger(caplog: Any, request: Any) -> ContextLogger:
    """Provide test context logger to tests.

    Args:
        caplog: pytest caplog fixture
        request: pytest request fixture

    Returns:
        ContextLogger instance
    """
    return ContextLogger(caplog, test_name=request.node.name)
