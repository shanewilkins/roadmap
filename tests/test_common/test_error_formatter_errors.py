"""
Comprehensive error path tests for error_formatter module.

Tests cover:
- format_error_message with various exception types
- format_warning_message with different inputs
- format_info_message edge cases
- format_success_message variations
- Plain mode vs rich mode output
- Empty/None/special character handling
"""

import unittest
from unittest.mock import patch

import pytest

from roadmap.common.error_formatter import (
    format_error_message,
    format_info_message,
    format_success_message,
    format_warning_message,
)
from roadmap.common.errors.exceptions import RoadmapException


class TestFormatErrorMessage(unittest.TestCase):
    """Test format_error_message function."""


# Move the parameterized test outside the class for pytest compatibility


@pytest.mark.parametrize(
    "exc,plain_mode,expected",
    [
        (
            RoadmapException(
                domain_message="Technical error", user_message="User-friendly error"
            ),
            False,
            "❌ User-friendly error",
        ),
        (
            RoadmapException(
                domain_message="Technical error", user_message="User-friendly error"
            ),
            True,
            "[ERROR] User-friendly error",
        ),
        (ValueError("Something went wrong"), False, "❌ Something went wrong"),
        (ValueError("Something went wrong"), True, "[ERROR] Something went wrong"),
        (
            RoadmapException(
                domain_message="Technical error", user_message="Default message"
            ),
            False,
            "❌ Default message",
        ),
        (
            RoadmapException(
                domain_message="Technical error",
                user_message="Line 1\nLine 2\nLine 3",
            ),
            False,
            "❌ Line 1\nLine 2\nLine 3",
        ),
        (
            RoadmapException(
                domain_message="Technical",
                user_message="Error with special chars: @#$%^&*()",
            ),
            False,
            "❌ Error with special chars: @#$%^&*()",
        ),
        (
            RoadmapException(
                domain_message="Technical",
                user_message="Error with unicode: 你好世界 🚀",
            ),
            False,
            "❌ Error with unicode: 你好世界 🚀",
        ),
        (
            RuntimeError("Runtime error occurred"),
            False,
            "❌ Runtime error occurred",
        ),
        (TypeError("Type mismatch error"), False, "❌ Type mismatch error"),
        (
            RoadmapException(
                domain_message="Technical", user_message="{}".format("A" * 50)
            ),
            False,
            "❌ {}".format("A" * 50),
        ),
        (
            RoadmapException(
                domain_message="Technical implementation",
                user_message="User-visible error",
            ),
            False,
            "❌ User-visible error",
        ),
    ],
)
def test_format_error_param(exc, plain_mode, expected):
    with patch("roadmap.common.error_formatter.is_plain_mode", return_value=plain_mode):
        result = format_error_message(exc)
    assert result == expected


class TestFormatWarningMessage(unittest.TestCase):
    """Test format_warning_message function."""

    def test_format_warning_rich_mode(self):
        """Warning message in rich mode should use emoji."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message("Be careful")

        assert result == "⚠️  Be careful"

    def test_format_warning_plain_mode(self):
        """Warning message in plain mode should use [WARN] tag."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=True):
            result = format_warning_message("Be careful")

        assert result == "[WARN] Be careful"

    def test_format_warning_empty_message(self):
        """Empty warning message should still format."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message("")

        assert result == "⚠️  "

    def test_format_warning_with_multiline(self):
        """Multiline warning messages should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message("Line 1\nLine 2")

        assert result == "⚠️  Line 1\nLine 2"

    def test_format_warning_with_special_characters(self):
        """Special characters should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message("Warning: test@example.com")

        assert result == "⚠️  Warning: test@example.com"

    def test_format_warning_with_unicode(self):
        """Unicode should be preserved in warning messages."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message("警告: 注意 ⚡")

        assert result == "⚠️  警告: 注意 ⚡"

    def test_format_warning_with_long_message(self):
        """Long warning messages should be preserved."""
        long_message = "B" * 500
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message(long_message)

        assert result == "⚠️  " + long_message

    def test_format_warning_with_quotes(self):
        """Quotes should be preserved in warning messages."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message('Warning: "quoted text"')

        assert result == '⚠️  Warning: "quoted text"'


class TestFormatInfoMessage(unittest.TestCase):
    """Test format_info_message function."""

    def test_format_info_rich_mode(self):
        """Info message in rich mode should use emoji."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message("Just so you know")

        assert result == "ℹ️  Just so you know"

    def test_format_info_plain_mode(self):
        """Info message in plain mode should use [INFO] tag."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=True):
            result = format_info_message("Just a heads up")

        assert result == "[INFO] Just a heads up"

    def test_format_info_with_multiline(self):
        """Multiline info messages should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message("First\nSecond\nThird")

        assert result == "ℹ️  First\nSecond\nThird"

    def test_format_info_with_special_characters(self):
        """Special characters should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message("Info: user@domain.com (verified)")

        assert result == "ℹ️  Info: user@domain.com (verified)"

    def test_format_info_with_unicode(self):
        """Unicode should be preserved in info messages."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message("信息: 处理完成 ✓")

        assert result == "ℹ️  信息: 处理完成 ✓"

    def test_format_info_with_long_message(self):
        """Long info messages should be preserved."""
        long_message = "C" * 500
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message(long_message)

        assert result == "ℹ️  " + long_message

    def test_format_info_with_paths(self):
        """File paths should be preserved in info messages."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message("Saved to /path/to/file.txt")

        assert result == "ℹ️  Saved to /path/to/file.txt"

    def test_format_info_with_urls(self):
        """URLs should be preserved in info messages."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message("More info at https://example.com/help")

        assert result == "ℹ️  More info at https://example.com/help"


class TestFormatSuccessMessage(unittest.TestCase):
    """Test format_success_message function."""

    def test_format_success_rich_mode(self):
        """Success message in rich mode should use emoji."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("All done!")

        assert result == "✅ All done!"

    def test_format_success_plain_mode(self):
        """Success message in plain mode should use [OK] tag."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=True):
            result = format_success_message("All done!")

        assert result == "[OK] All done!"

    def test_format_success_empty_message(self):
        """Empty success message should still format."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("")

        assert result == "✅ "

    def test_format_success_with_multiline(self):
        """Multiline success messages should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("Complete\nVerified\nReady")

        assert result == "✅ Complete\nVerified\nReady"

    def test_format_success_with_special_characters(self):
        """Special characters should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("Processed 100% of items")

        assert result == "✅ Processed 100% of items"

    def test_format_success_with_unicode(self):
        """Unicode should be preserved in success messages."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("成功: 任务完成 🎉")

        assert result == "✅ 成功: 任务完成 🎉"

    def test_format_success_with_long_message(self):
        """Long success messages should be preserved."""
        long_message = "D" * 500
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message(long_message)

        assert result == "✅ " + long_message

    def test_format_success_with_counts(self):
        """Messages with counts should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("Created 42 items")

        assert result == "✅ Created 42 items"

    def test_format_success_with_ids(self):
        """Messages with IDs should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("Issue #12345 resolved")

        assert result == "✅ Issue #12345 resolved"


class TestPlainModeDetection(unittest.TestCase):
    """Test plain mode detection across all formatters."""

    def test_all_formatters_respect_plain_mode(self):
        """All formatters should respect plain mode setting."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=True):
            error = format_error_message(ValueError("test"))
            warning = format_warning_message("test")
            info = format_info_message("test")
            success = format_success_message("test")

        assert error.startswith("[ERROR]")
        assert warning.startswith("[WARN]")
        assert info.startswith("[INFO]")
        assert success.startswith("[OK]")

    def test_all_formatters_use_emoji_in_rich_mode(self):
        """All formatters should use emoji in rich mode."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            error = format_error_message(ValueError("test"))
            warning = format_warning_message("test")
            info = format_info_message("test")
            success = format_success_message("test")

        assert error.startswith("❌")
        assert warning.startswith("⚠️")
        assert info.startswith("ℹ️")
        assert success.startswith("✅")


class TestErrorFormatterEdgeCases(unittest.TestCase):
    """Test edge cases across error formatter."""

    def test_exception_with_none_str_representation(self):
        """Exception with None-like str should be handled."""
        exc = Exception()
        exc.__str__ = lambda: ""

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_error_message(exc)

        assert result == "❌ "

    def test_very_long_exception_message(self):
        """Very long exception messages should be preserved."""
        long_msg = "X" * 10000
        exc = ValueError(long_msg)

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_error_message(exc)

        assert len(result) == len(long_msg) + 2  # emoji + space + message

    def test_exception_message_with_newlines_and_tabs(self):
        """Exception messages with whitespace variants should be preserved."""
        exc = ValueError("Line1\t\tTab\nLine2\nLine3")

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_error_message(exc)

        assert "Line1\t\tTab" in result
        assert "Line2" in result

    def test_formatter_idempotency(self):
        """Formatting the same message multiple times should yield same result."""
        msg = "Test message"

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result1 = format_info_message(msg)
            result2 = format_info_message(msg)
            result3 = format_info_message(msg)

        assert result1 == result2 == result3

    def test_mixed_emoji_in_user_message(self):
        """User messages containing emoji should be preserved."""
        exc = RoadmapException(
            domain_message="Tech",
            user_message="Status: 🔴 Error, 🟡 Warning, 🟢 OK",
        )

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_error_message(exc)

        assert "🔴" in result and "🟡" in result and "🟢" in result

    def test_ansi_codes_in_message_preserved(self):
        """ANSI codes in messages should be preserved (even if redundant)."""
        msg = "Message with \033[1mbold\033[0m"

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message(msg)

        assert "\033[1mbold\033[0m" in result

    def test_percent_signs_in_message(self):
        """Percent signs should not cause formatting issues."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_success_message("Progress: 100%")

        assert result == "✅ Progress: 100%"

    def test_curly_braces_in_message(self):
        """Curly braces should not cause issues."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_info_message("Variables: {a}, {b}, {c}")

        assert result == "ℹ️  Variables: {a}, {b}, {c}"

    def test_backslash_in_message(self):
        """Backslashes should be preserved."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_warning_message("Path: C:\\Users\\Name")

        assert result == "⚠️  Path: C:\\Users\\Name"


class TestErrorFormatterIntegration(unittest.TestCase):
    """Integration tests for error formatter."""

    def test_roadmap_exception_preserves_domain_message(self):
        """RoadmapException domain_message should not appear in output."""
        exc = RoadmapException(
            domain_message="Technical implementation details",
            user_message="Something went wrong",
        )

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            result = format_error_message(exc)

        assert "Technical implementation details" not in result
        assert "Something went wrong" in result

    def test_exception_type_doesnt_affect_formatting(self):
        """Different exception types should format similarly."""
        exceptions = [
            ValueError("Test error"),
            TypeError("Test error"),
            RuntimeError("Test error"),
            KeyError("Test error"),
        ]

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            results = [format_error_message(exc) for exc in exceptions]

        assert all(r.startswith("❌ ") for r in results)
        assert all("Test error" in r for r in results)

    def test_all_formatters_with_same_message(self):
        """All formatters should handle same message consistently."""
        message = "Test message"

        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            error = format_error_message(ValueError(message))
            warning = format_warning_message(message)
            info = format_info_message(message)
            success = format_success_message(message)

        assert all(message in result for result in [error, warning, info, success])

    def test_formatter_output_format_consistency(self):
        """All formatters should follow emoji + space + message format (or space + emoji)."""
        with patch("roadmap.common.error_formatter.is_plain_mode", return_value=False):
            error = format_error_message(ValueError("msg"))
            warning = format_warning_message("msg")
            info = format_info_message("msg")
            success = format_success_message("msg")

            # Check that each has emoji and message
            assert error == "❌ msg"
            assert warning == "⚠️  msg"
            assert info == "ℹ️  msg"
            assert success == "✅ msg"
