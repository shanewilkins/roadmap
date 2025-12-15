"""Output and I/O fixtures for CLI testing.

Provides utilities for handling CLI output formatting, ANSI stripping, and output validation.
"""

import pytest

from tests.unit.shared.test_utils import (
    assert_in_output,
    assert_output_contains,
    clean_cli_output,
    strip_ansi,
)


@pytest.fixture
def strip_ansi_fixture():
    """Provide ANSI stripping utility to tests."""
    return strip_ansi


@pytest.fixture
def clean_output():
    """Provide CLI output cleaning utility to tests."""
    return clean_cli_output


@pytest.fixture
def assert_output():
    """Provide output assertion helpers to tests.

    Returns a dict with assertion functions:
        assert_in: Check if text is in output
        assert_contains: Check if output contains text
        clean: Clean output of ANSI codes
        strip: Strip ANSI codes from text
    """
    return {
        "assert_in": assert_in_output,
        "assert_contains": assert_output_contains,
        "clean": clean_cli_output,
        "strip": strip_ansi,
    }
