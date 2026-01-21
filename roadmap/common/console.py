"""Console utilities for CLI operations.

Provides centralized console instances configured for the current environment:
- get_console() → Rich console for successful output (stdout)
- get_console_stderr() → Console for errors/warnings (stderr)
- is_plain_mode() → Auto-detect plain text mode for POSIX compliance

Plain mode is auto-detected based on:
- Output is not a terminal (piped/redirected)
- ROADMAP_OUTPUT=plain environment variable
- NO_COLOR=1 environment variable
- Running in CI/CD environment

This separation ensures:
- Success output to stdout (can be piped, has colors)
- Errors to stderr (never interferes with data)
- POSIX compliance (no ANSI codes when piped)
- Machine-readable output (can parse stdout, ignore stderr)
"""

import os
import sys

from rich.console import Console


def is_plain_mode() -> bool:
    """Detect if we should use plain text output (no ANSI codes).

    Returns True if any of:
    - Output is redirected/piped (not a terminal)
    - ROADMAP_OUTPUT=plain environment variable set
    - NO_COLOR=1 for POSIX compliance
    - Running in CI/CD environment
    - In testing environment

    Returns:
        bool: True if plain mode should be used
    """
    return any(
        [
            # Explicit plain mode request
            os.environ.get("ROADMAP_OUTPUT") == "plain",
            # POSIX NO_COLOR standard
            os.environ.get("NO_COLOR") in ("1", "true", "True", "TRUE"),
            # User forced no colors
            os.environ.get("FORCE_COLOR") == "0",
            # Output is piped/redirected (not interactive)
            not sys.stdout.isatty(),
            not sys.stderr.isatty(),
            # CI/CD environments
            any(
                ci_var in os.environ
                for ci_var in [
                    "CI",
                    "CONTINUOUS_INTEGRATION",
                    "GITHUB_ACTIONS",
                    "TRAVIS",
                    "CIRCLECI",
                    "JENKINS_URL",
                    "GITLAB_CI",
                ]
            ),
            # Testing environment
            any(
                test_var in os.environ
                for test_var in [
                    "PYTEST_CURRENT_TEST",
                    "_PYTEST_RAISE",
                    "UNITTEST_MODE",
                ]
            ),
        ]
    )


def is_testing_environment() -> bool:
    """Detect if we're running in a testing environment.

    Returns True if any of the following conditions are met:
    - pytest is running
    - NO_COLOR environment variable is set
    - TERM is set to 'dumb'
    - Output is not a terminal
    - Running under CI/CD
    """
    return any(
        [
            # Pytest detection
            "PYTEST_CURRENT_TEST" in os.environ,
            "pytest" in sys.modules,
            hasattr(sys, "_called_from_test"),
            # Explicit color disabling
            os.environ.get("NO_COLOR") in ("1", "true", "True", "TRUE"),
            os.environ.get("FORCE_COLOR") == "0",
            # Terminal detection
            os.environ.get("TERM") in ("dumb", ""),
            not sys.stdout.isatty(),
            not sys.stderr.isatty(),
            # CI/CD environments
            any(
                ci_var in os.environ
                for ci_var in [
                    "CI",
                    "CONTINUOUS_INTEGRATION",
                    "GITHUB_ACTIONS",
                    "TRAVIS",
                    "CIRCLECI",
                    "JENKINS_URL",
                    "GITLAB_CI",
                ]
            ),
            # Test frameworks
            any(
                test_var in os.environ
                for test_var in [
                    "PYTEST_CURRENT_TEST",
                    "_PYTEST_RAISE",
                    "UNITTEST_MODE",
                ]
            ),
        ]
    )


def get_console() -> Console:
    """Get a console instance configured for successful output (stdout).

    Returns a console configured for:
    - Rich output when in interactive terminal (colors, tables, styles)
    - Plain text output when piped/testing (POSIX compliance)
    - No ANSI codes when plain mode is detected

    Returns a fresh instance each time to ensure file handle is current.

    Returns:
        Console: Configured Rich Console instance
    """
    plain = is_plain_mode()

    # Use fresh instance each time to ensure file handle is correct
    # This is critical for testing with CliRunner which replaces sys.stdout
    if plain:
        return Console(
            file=sys.stdout,
            force_terminal=False,
            no_color=True,
            width=80,
            legacy_windows=False,
            force_interactive=False,
            force_jupyter=False,
        )

    # Interactive mode: full Rich features
    return Console(file=sys.stdout)


def get_console_stderr() -> Console:
    """Get a console instance configured for error output (stderr).

    Returns a console that outputs to stderr for:
    - Error messages
    - Warnings
    - Diagnostic information

    This ensures errors don't interfere with stdout data.

    Returns:
        Console: Console instance writing to stderr
    """
    plain = is_plain_mode()

    # In testing/plain mode: no terminal, no colors
    if plain:
        return Console(
            file=sys.stderr,
            force_terminal=False,
            no_color=True,
            width=80,
            legacy_windows=False,
        )

    # Interactive mode: use stderr with colors
    return Console(file=sys.stderr)
