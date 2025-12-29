"""Test data factories for consistent and reusable test data generation."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest

# Mark all tests in this file as unit tests (no filesystem operations)
pytestmark = pytest.mark.unit


class TestDataFactory:
    """Factory for generating consistent test data across test suites."""

    @staticmethod
    def create_cli_test_data(**kwargs) -> dict[str, Any]:
        """Create test data for CLI command testing.

        Args:
            **kwargs: Override default CLI test data

        Returns:
            Dict: CLI test data including commands, inputs, and expected outputs
        """
        return {
            "commands": kwargs.get(
                "commands",
                [
                    "roadmap init",
                    'roadmap add "Test Issue"',
                    "roadmap list",
                    "roadmap status",
                ],
            ),
            "inputs": kwargs.get(
                "inputs",
                {
                    "project_name": "Test CLI Project",
                    "owner": "cli-test-owner",
                    "repository": "cli-test-repo",
                },
            ),
            "expected_outputs": kwargs.get(
                "expected_outputs",
                {
                    "init_success": "Roadmap initialized successfully",
                    "add_success": "Issue added successfully",
                    "list_header": "ID",
                    "status_ready": "roadmap is ready",
                },
            ),
        }

    # ========== Error/Exception Fixtures (Phase 10a-c) ==========

    @staticmethod
    def create_validation_error(**kwargs) -> Exception:
        """Create a validation error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                field: Field that failed validation
                value: Invalid value provided

        Returns:
            Exception: Validation error
        """
        message = kwargs.get("message", "Validation failed")
        field = kwargs.get("field", "test_field")
        value = kwargs.get("value", "invalid_value")
        return ValueError(f"{message}: {field}={value}")

    @staticmethod
    def create_permission_error(**kwargs) -> Exception:
        """Create a permission error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                path: Path that failed permission check
                operation: Operation that failed (read/write/execute)

        Returns:
            Exception: Permission error
        """
        message = kwargs.get("message", "Permission denied")
        path = kwargs.get("path", "/test/path")
        operation = kwargs.get("operation", "read")
        return PermissionError(f"{message}: {operation} on {path}")

    @staticmethod
    def create_network_error(**kwargs) -> Exception:
        """Create a network error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                status_code: HTTP status code
                endpoint: API endpoint that failed

        Returns:
            Exception: Network/connection error
        """
        message = kwargs.get("message", "Network error")
        status_code = kwargs.get("status_code", 500)
        endpoint = kwargs.get("endpoint", "https://api.example.com/test")
        return RuntimeError(f"{message}: {status_code} from {endpoint}")

    @staticmethod
    def create_file_not_found_error(**kwargs) -> Exception:
        """Create a file not found error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                path: File path that was not found

        Returns:
            Exception: File not found error
        """
        message = kwargs.get("message", "File not found")
        path = kwargs.get("path", "/test/missing/file.txt")
        return FileNotFoundError(f"{message}: {path}")

    @staticmethod
    def create_timeout_error(**kwargs) -> Exception:
        """Create a timeout error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                timeout_seconds: Timeout duration

        Returns:
            Exception: Timeout error
        """
        message = kwargs.get("message", "Operation timed out")
        timeout_seconds = kwargs.get("timeout_seconds", 30)
        return TimeoutError(f"{message} after {timeout_seconds}s")

    @staticmethod
    def create_git_commit(**kwargs) -> Mock:
        """Create a mock Git commit for testing.

        Args:
            **kwargs: Override commit properties
                sha: Commit hash
                message: Commit message
                author: Author name
                timestamp: Commit timestamp
                files: Changed files

        Returns:
            Mock: Configured Git commit object
        """

        commit = Mock()
        commit.sha = kwargs.get("sha", "abc123def456")
        commit.message = kwargs.get("message", "Test commit message")
        commit.author = kwargs.get("author", "Test Author")
        commit.timestamp = kwargs.get("timestamp", datetime.now(timezone.utc))
        commit.files = kwargs.get("files", ["file1.py", "file2.py"])
        return commit

    @staticmethod
    def create_git_status(**kwargs) -> Mock:
        """Create a mock Git status for testing.

        Args:
            **kwargs: Override status properties
                branch: Current branch name
                modified: List of modified files
                untracked: List of untracked files
                staged: List of staged files
                is_dirty: Whether working directory is dirty

        Returns:
            Mock: Configured Git status object
        """
        status = Mock()
        status.branch = kwargs.get("branch", "main")
        status.modified = kwargs.get("modified", [])
        status.untracked = kwargs.get("untracked", [])
        status.staged = kwargs.get("staged", [])
        status.is_dirty = kwargs.get("is_dirty", False)
        return status

    @staticmethod
    def create_github_api_error(**kwargs) -> dict[str, Any]:
        """Create a GitHub API error response for testing error paths.

        Args:
            **kwargs: Override error properties
                status_code: HTTP status code
                message: Error message
                error_code: GitHub error code
                documentation_url: Link to docs

        Returns:
            Dict: GitHub API error response
        """
        return {
            "message": kwargs.get("message", "API Error"),
            "status_code": kwargs.get("status_code", 400),
            "error_code": kwargs.get("error_code", "validation_failed"),
            "documentation_url": kwargs.get(
                "documentation_url", "https://docs.github.com/api"
            ),
        }

    @staticmethod
    def create_command_execution_context(**kwargs) -> Mock:
        """Create a command execution context for testing.

        Args:
            **kwargs: Override context properties
                working_dir: Working directory
                environment: Environment variables
                timeout: Execution timeout
                capture_output: Whether to capture output

        Returns:
            Mock: Command execution context
        """
        from pathlib import Path

        context = Mock()
        context.working_dir = kwargs.get("working_dir", Path("/test"))
        context.environment = kwargs.get("environment", {})
        context.timeout = kwargs.get("timeout", 30)
        context.capture_output = kwargs.get("capture_output", True)
        return context
