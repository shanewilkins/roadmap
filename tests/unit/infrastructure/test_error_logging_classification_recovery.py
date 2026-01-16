"""Comprehensive unit tests for error logging module.

Tests cover error classification, recovery suggestion, and all error logging functions.
"""

import pytest

from roadmap.common.logging.error_logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    suggest_recovery,
)


class TestErrorClassification:
    """Test ErrorClassification constants."""

    def test_error_classification_constants(self):
        """Test that classification constants are defined."""
        assert ErrorClassification.USER_ERROR == "user_error"
        assert ErrorClassification.SYSTEM_ERROR == "system_error"
        assert ErrorClassification.EXTERNAL_ERROR == "external_error"
        assert ErrorClassification.UNKNOWN_ERROR == "unknown_error"


class TestClassifyError:
    """Test classify_error function."""

    @pytest.mark.parametrize(
        "error,expected_classification",
        [
            (ValueError("Bad value"), ErrorClassification.USER_ERROR),
            (TypeError("Type mismatch"), ErrorClassification.USER_ERROR),
            (KeyError("Missing key"), ErrorClassification.USER_ERROR),
            (OSError("File not found"), ErrorClassification.SYSTEM_ERROR),
            (FileNotFoundError("Missing file"), ErrorClassification.SYSTEM_ERROR),
            (PermissionError("Access denied"), ErrorClassification.SYSTEM_ERROR),
            (ConnectionError("Connection failed"), ErrorClassification.SYSTEM_ERROR),
            (TimeoutError("Request timeout"), ErrorClassification.SYSTEM_ERROR),
            (RuntimeError("Runtime problem"), ErrorClassification.UNKNOWN_ERROR),
            (Exception("Unknown error"), ErrorClassification.UNKNOWN_ERROR),
        ],
    )
    def test_classify_error(self, error, expected_classification):
        """Test classification of various error types.

        Covers lines 34-103: Error classification for all major error types
        """
        result = classify_error(error)
        assert result == expected_classification

    def test_classify_validation_error(self):
        """Test classification of ValidationError."""
        from roadmap.common.errors import ValidationError

        error = ValidationError("Invalid value")
        result = classify_error(error)
        assert result == ErrorClassification.USER_ERROR


class TestIsErrorRecoverable:
    """Test is_error_recoverable function."""

    @pytest.mark.parametrize(
        "error,is_recoverable",
        [
            (ConnectionError("Network issue"), True),
            (TimeoutError("Request timeout"), True),
            (BlockingIOError("Blocking I/O"), True),
            (BrokenPipeError("Pipe broken"), True),
            (ValueError("Bad value"), False),
            (OSError("File issue"), False),
            (RuntimeError("Runtime problem"), False),
        ],
    )
    def test_is_error_recoverable(self, error, is_recoverable):
        """Test recoverability classification for various error types.

        Covers lines 108-142: Recoverability assessment for all major error types
        """
        assert is_error_recoverable(error) is is_recoverable


class TestSuggestRecovery:
    """Test suggest_recovery function."""

    @pytest.mark.parametrize(
        "error,expected_action",
        [
            (ConnectionError("Connection failed"), "retry"),
            (TimeoutError("Timeout"), "retry"),
            (BlockingIOError("Blocking I/O"), "retry"),
            (ValueError("Bad value"), "validate_input"),
            (OSError("Permission denied"), "manual_intervention"),
            (RuntimeError("Unknown problem"), "contact_support"),
        ],
    )
    def test_suggest_recovery(self, error, expected_action):
        """Test recovery suggestions for various error types.

        Covers lines 147-190: Recovery action suggestions for all error types
        """
        result = suggest_recovery(error)
        assert result == expected_action

    def test_suggest_recovery_with_context(self):
        """Test recovery suggestion with context."""
        error = ValueError("Bad input")
        context = {"operation": "parsing", "field": "name"}
        result = suggest_recovery(error, context)
        assert result == "validate_input"
