"""Assertion helpers for common test patterns.

Provides convenient assertion functions for testing CLI output, exit codes,
file operations, and other common test patterns.
"""

from pathlib import Path
from typing import Any

import pytest

from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


class CLIAssertion:
    """Helper class for making CLI assertions in tests."""

    @staticmethod
    def exit_code(result: Any, expected: int, message: str = "") -> None:
        """Assert that a Click result has the expected exit code.

        Args:
            result: Click CliRunner result
            expected: Expected exit code
            message: Optional custom error message

        Raises:
            AssertionError: If exit code doesn't match
        """
        assert result.exit_code == expected, (
            f"Expected exit code {expected}, got {result.exit_code}. "
            f"{message}\nOutput: {result.output}"
        )

    @staticmethod
    def output_contains(result: Any, expected: str, clean: bool = True) -> None:
        """Assert that output contains expected text.

        Args:
            result: Click CliRunner result
            expected: Text to look for
            clean: Whether to clean ANSI codes before checking

        Raises:
            AssertionError: If expected text not in output
        """
        output = clean_cli_output(result.output) if clean else result.output
        assert (
            expected.lower() in output.lower()
        ), f"Expected '{expected}' not found in output.\nOutput: {output}"

    @staticmethod
    def output_not_contains(result: Any, unexpected: str, clean: bool = True) -> None:
        """Assert that output does NOT contain unexpected text.

        Args:
            result: Click CliRunner result
            unexpected: Text to NOT look for
            clean: Whether to clean ANSI codes before checking

        Raises:
            AssertionError: If unexpected text IS in output
        """
        output = clean_cli_output(result.output) if clean else result.output
        assert (
            unexpected.lower() not in output.lower()
        ), f"Unexpected '{unexpected}' found in output.\nOutput: {output}"

    @staticmethod
    def success(result: Any, message: str = "") -> None:
        """Assert that command succeeded (exit code 0).

        Args:
            result: Click CliRunner result
            message: Optional custom error message

        Raises:
            AssertionError: If command failed
        """
        CLIAssertion.exit_code(result, 0, message or "Command should succeed")

    @staticmethod
    def failure(result: Any, expected_code: int = 1, message: str = "") -> None:
        """Assert that command failed with expected exit code.

        Args:
            result: Click CliRunner result
            expected_code: Expected failure exit code (default: 1)
            message: Optional custom error message

        Raises:
            AssertionError: If exit code doesn't match
        """
        CLIAssertion.exit_code(result, expected_code, message or "Command should fail")

    @staticmethod
    def success_with_context(result: Any, context: str = "") -> None:
        """Assert that command succeeded with detailed error context if it fails.

        Provides comprehensive error information including output, exception,
        and optional context to help debug test failures.

        Args:
            result: Click CliRunner result
            context: Optional context description (e.g., "Issue creation", "Milestone update")

        Raises:
            AssertionError: If command failed, with detailed error information
        """
        if result.exit_code == 0:
            return

        error_msg = []
        if context:
            error_msg.append(f"Context: {context}")
        error_msg.append(f"Exit code: {result.exit_code}")
        error_msg.append(f"Output:\n{result.output}")
        if result.exception:
            import traceback

            error_msg.append(f"Exception: {result.exception}")
            error_msg.append(
                f"Traceback:\n{''.join(traceback.format_exception(type(result.exception), result.exception, result.exception.__traceback__))}"
            )

        raise AssertionError("\n".join(error_msg))

    @staticmethod
    def exit_code_with_output(
        result: Any, expected: int, show_output: bool = True, context: str = ""
    ) -> None:
        """Assert exit code with optional full output display.

        Useful for debugging: if the assertion fails, you get complete output
        and exception information.

        Args:
            result: Click CliRunner result
            expected: Expected exit code
            show_output: If True, include full output in error (default: True)
            context: Optional context description

        Raises:
            AssertionError: If exit code doesn't match, with comprehensive context
        """
        if result.exit_code == expected:
            return

        error_msg = []
        if context:
            error_msg.append(f"Context: {context}")
        error_msg.append(f"Expected exit code {expected}, got {result.exit_code}")
        if show_output:
            error_msg.append(f"Output:\n{result.output}")
        if result.exception:
            import traceback

            error_msg.append(
                f"Exception: {type(result.exception).__name__}: {result.exception}"
            )
            error_msg.append(
                f"Traceback:\n{''.join(traceback.format_exception(type(result.exception), result.exception, result.exception.__traceback__))}"
            )

        raise AssertionError("\n".join(error_msg))


class FileAssertion:
    """Helper class for making filesystem assertions in tests."""

    @staticmethod
    def exists(path: Path, message: str = "") -> None:
        """Assert that a file or directory exists.

        Args:
            path: Path to check
            message: Optional custom error message

        Raises:
            AssertionError: If path doesn't exist
        """
        assert path.exists(), f"Expected {path} to exist. {message}"

    @staticmethod
    def not_exists(path: Path, message: str = "") -> None:
        """Assert that a file or directory does NOT exist.

        Args:
            path: Path to check
            message: Optional custom error message

        Raises:
            AssertionError: If path exists
        """
        assert not path.exists(), f"Expected {path} to not exist. {message}"

    @staticmethod
    def is_file(path: Path, message: str = "") -> None:
        """Assert that path is a file.

        Args:
            path: Path to check
            message: Optional custom error message

        Raises:
            AssertionError: If path is not a file
        """
        assert path.is_file(), f"Expected {path} to be a file. {message}"

    @staticmethod
    def is_dir(path: Path, message: str = "") -> None:
        """Assert that path is a directory.

        Args:
            path: Path to check
            message: Optional custom error message

        Raises:
            AssertionError: If path is not a directory
        """
        assert path.is_dir(), f"Expected {path} to be a directory. {message}"

    @staticmethod
    def contains(path: Path, content: str, message: str = "") -> None:
        """Assert that file contains expected content.

        Args:
            path: Path to file
            content: Content to look for
            message: Optional custom error message

        Raises:
            AssertionError: If content not found or file doesn't exist
        """
        assert path.exists(), f"File {path} doesn't exist. {message}"
        file_content = path.read_text()
        assert content in file_content, (
            f"Expected content not found in {path}. {message}\n"
            f"File content: {file_content}"
        )

    @staticmethod
    def not_contains(path: Path, content: str, message: str = "") -> None:
        """Assert that file does NOT contain unexpected content.

        Args:
            path: Path to file
            content: Content to NOT look for
            message: Optional custom error message

        Raises:
            AssertionError: If content found or file doesn't exist
        """
        assert path.exists(), f"File {path} doesn't exist. {message}"
        file_content = path.read_text()
        assert content not in file_content, (
            f"Unexpected content found in {path}. {message}\n"
            f"File content: {file_content}"
        )


@pytest.fixture
def assert_cli():
    """Provide CLI assertion helpers to tests.

    Returns:
        CLIAssertion class with static methods for common assertions
    """
    return CLIAssertion


@pytest.fixture
def assert_file():
    """Provide filesystem assertion helpers to tests.

    Returns:
        FileAssertion class with static methods for file assertions
    """
    return FileAssertion
