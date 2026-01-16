"""
Test utilities for handling CLI output formatting.
"""

import re
from typing import cast


def strip_ansi(text: str | bytes) -> str:
    """
    Remove ANSI escape sequences from text.

    This function removes all ANSI color codes, formatting codes, and cursor
    control sequences to get clean text for test assertions.

    Args:
        text: String or bytes containing ANSI escape sequences

    Returns:
        Clean string with all ANSI sequences removed

    Examples:
        >>> strip_ansi("\x1b[1;32m✅ Success\x1b[0m")
        "✅ Success"
        >>> strip_ansi("\x1b[1mBold\x1b[0m normal text")
        "Bold normal text"
    """
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")

    # Ensure type is str for Pyright
    text = cast(str, text)

    # Comprehensive ANSI escape sequence patterns
    ansi_patterns = [
        r"\x1b\[[0-9;]*[mGKHJABCDEFnuslh]",  # Standard ANSI sequences
        r"\x1b\[[0-9;]*[ABCDEFGHJKSTmhl]",  # Cursor control and formatting
        r"\x1b\([AB]",  # Character set selection
        r"\x1b\].*?\x07",  # OSC sequences (title, etc.)
        r"\x1b\].*?\x1b\\",  # OSC sequences with ST terminator
        r"\x1b[=>]",  # Application keypad
        r"\x1b[HJ]",  # Clear screen variants
        r"\x1b7\x1b8",  # Save/restore cursor position
    ]

    # Combine all patterns into one
    combined_pattern = "|".join(ansi_patterns)
    ansi_escape = re.compile(combined_pattern)

    # Remove ANSI sequences
    clean_text = ansi_escape.sub("", text)

    # Clean up any remaining control characters except newlines and tabs
    clean_text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "", clean_text)

    return clean_text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text for consistent test comparisons.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single spaces
    text = re.sub(r" +", " ", text)
    # Replace multiple newlines with single newlines
    text = re.sub(r"\n+", "\n", text)
    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def clean_cli_output(text: str) -> str:
    """
    Clean CLI output for test assertions by removing ANSI codes and normalizing whitespace.

    This is a convenience function that combines ANSI stripping with whitespace
    normalization for consistent test assertions.

    Args:
        text: Raw CLI output text

    Returns:
        Clean text suitable for test assertions
    """
    clean = strip_ansi(text)
    return normalize_whitespace(clean)


def assert_in_output(expected: str, actual_output: str, clean: bool = True) -> bool:
    """
    Check if expected text is in CLI output, with optional cleaning.

    Args:
        expected: Text to look for
        actual_output: CLI output to search in
        clean: Whether to clean ANSI codes and normalize whitespace

    Returns:
        True if expected text found in output
    """
    if clean:
        return expected in clean_cli_output(actual_output)
    else:
        return expected in actual_output


def assert_output_contains(
    expected_lines: list[str], actual_output: str, clean: bool = True
) -> bool:
    """
    Check if all expected lines are present in CLI output.

    Args:
        expected_lines: List of text lines to look for
        actual_output: CLI output to search in
        clean: Whether to clean ANSI codes and normalize whitespace

    Returns:
        True if all expected lines found in output
    """
    if clean:
        cleaned_output = clean_cli_output(actual_output)
    else:
        cleaned_output = actual_output

    return all(line in cleaned_output for line in expected_lines)
