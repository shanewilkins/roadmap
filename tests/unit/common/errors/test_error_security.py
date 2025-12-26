"""Tests for parsing and security related error classes."""

from pathlib import Path

import pytest

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity
from roadmap.common.errors.error_security import (
    ParseError,
    PathValidationError,
    SecurityError,
)


class TestParseError:
    """Tests for ParseError class."""

    def test_parse_error_basic(self):
        """Test basic ParseError."""
        error = ParseError("Invalid syntax")

        assert error.message == "Invalid syntax"
        assert error.category == ErrorCategory.PARSING
        assert error.severity == ErrorSeverity.HIGH
        assert error.file_path is None
        assert error.line_number is None

    def test_parse_error_with_file_path_string(self):
        """Test ParseError with string file path."""
        error = ParseError("Unexpected token", file_path=".roadmap/issues/test.md")

        assert error.message == "Unexpected token"
        assert error.file_path == ".roadmap/issues/test.md"
        assert "file_path" in error.context
        assert error.context["file_path"] == ".roadmap/issues/test.md"

    def test_parse_error_with_file_path_object(self):
        """Test ParseError with Path object."""
        file_path = Path(".roadmap/issues/test.md")
        error = ParseError("Parse failed", file_path=file_path)

        assert error.file_path == file_path
        assert error.context["file_path"] == str(file_path)

    def test_parse_error_with_line_number(self):
        """Test ParseError with line number."""
        error = ParseError("Syntax error", line_number=42)

        assert error.line_number == 42
        assert "line_number" in error.context
        assert error.context["line_number"] == 42

    def test_parse_error_with_all_fields(self):
        """Test ParseError with all fields."""
        file_path = Path("config.yaml")
        error = ParseError("Invalid YAML", file_path=file_path, line_number=15)

        assert error.message == "Invalid YAML"
        assert error.file_path == file_path
        assert error.line_number == 15
        assert error.context["file_path"] == str(file_path)
        assert error.context["line_number"] == 15

    def test_parse_error_custom_severity(self):
        """Test ParseError with custom severity."""
        error = ParseError("Critical parse error", severity=ErrorSeverity.CRITICAL)

        assert error.severity == ErrorSeverity.CRITICAL

    def test_parse_error_with_cause(self):
        """Test ParseError with cause."""
        cause = ValueError("Invalid format")
        error = ParseError("Failed to parse", cause=cause)

        assert error.cause is cause

    @pytest.mark.parametrize(
        "line_number",
        [1, 10, 100, 1000, 9999],
    )
    def test_parse_error_various_line_numbers(self, line_number):
        """Test ParseError with various line numbers."""
        error = ParseError("Parse error", line_number=line_number)

        assert error.line_number == line_number
        assert error.context["line_number"] == line_number

    def test_parse_error_zero_line_number(self):
        """Test ParseError with zero line number (edge case)."""
        # Line number 0 is falsy, so it won't be included in context
        error = ParseError("Parse error", line_number=0)

        # 0 is falsy, so line_number won't be added to context
        assert error.line_number == 0
        assert "line_number" not in error.context


class TestSecurityError:
    """Tests for SecurityError class."""

    def test_security_error_basic(self):
        """Test basic SecurityError."""
        error = SecurityError("Unauthorized access")

        assert error.message == "Unauthorized access"
        assert error.category == ErrorCategory.PERMISSION
        assert error.severity == ErrorSeverity.CRITICAL

    def test_security_error_custom_severity(self):
        """Test SecurityError with custom severity."""
        error = SecurityError("Minor security issue", severity=ErrorSeverity.HIGH)

        assert error.severity == ErrorSeverity.HIGH

    def test_security_error_with_context(self):
        """Test SecurityError with additional context."""
        error = SecurityError(
            "Permission denied", context={"resource": "config", "action": "write"}
        )

        assert "resource" in error.context
        assert "action" in error.context
        assert error.context["resource"] == "config"
        assert error.context["action"] == "write"

    def test_security_error_with_cause(self):
        """Test SecurityError with cause."""
        cause = PermissionError("Access denied")
        error = SecurityError("Security violation", cause=cause)

        assert error.cause is cause

    @pytest.mark.parametrize(
        "message",
        [
            "Unauthorized access",
            "Permission denied",
            "Access control violation",
            "Authentication failed",
        ],
    )
    def test_security_error_various_messages(self, message):
        """Test SecurityError with various messages."""
        error = SecurityError(message)

        assert error.message == message


class TestPathValidationError:
    """Tests for PathValidationError class."""

    def test_path_validation_error_basic(self):
        """Test basic PathValidationError."""
        error = PathValidationError("Invalid path")

        assert error.message == "Invalid path"
        assert error.category == ErrorCategory.PERMISSION
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.path is None

    def test_path_validation_error_with_string_path(self):
        """Test PathValidationError with string path."""
        error = PathValidationError(
            "Path traversal detected", path="../../../etc/passwd"
        )

        assert error.message == "Path traversal detected"
        assert error.path == "../../../etc/passwd"
        assert "path" in error.context
        assert error.context["path"] == "../../../etc/passwd"

    def test_path_validation_error_with_path_object(self):
        """Test PathValidationError with Path object."""
        path = Path(".roadmap/issues/test.md")
        error = PathValidationError("Invalid path", path=path)

        assert error.path == path
        assert error.context["path"] == str(path)

    def test_path_validation_error_traversal_attack(self):
        """Test PathValidationError for path traversal attack."""
        dangerous_path = "../../sensitive_file"
        error = PathValidationError(
            "Path traversal attack detected", path=dangerous_path
        )

        assert error.path == dangerous_path
        assert error.context["path"] == dangerous_path

    def test_path_validation_error_custom_severity(self):
        """Test PathValidationError with custom severity."""
        error = PathValidationError("Path issue", severity=ErrorSeverity.HIGH)

        assert error.severity == ErrorSeverity.HIGH

    def test_path_validation_error_with_additional_context(self):
        """Test PathValidationError inherits additional context from parent."""
        error = PathValidationError("Invalid path", path="/home/user/.roadmap")

        assert error.path == "/home/user/.roadmap"
        assert "path" in error.context
        assert error.context["path"] == "/home/user/.roadmap"

    @pytest.mark.parametrize(
        "path,reason",
        [
            ("../../../etc/passwd", "traversal"),
            ("~/.ssh/id_rsa", "home_access"),
            ("/etc/shadow", "system_file"),
            ("./../../secret", "relative_traversal"),
        ],
    )
    def test_path_validation_error_various_paths(self, path, reason):
        """Test PathValidationError with various problematic paths."""
        error = PathValidationError(f"Invalid path: {reason}", path=path)

        assert error.path == path
        assert error.context["path"] == path

    def test_path_validation_error_inheritance(self):
        """Test that PathValidationError inherits from SecurityError."""
        error = PathValidationError("Test error")

        assert isinstance(error, SecurityError)
        assert error.category == ErrorCategory.PERMISSION
