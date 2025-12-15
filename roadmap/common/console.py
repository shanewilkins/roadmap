"""
Console utilities for CLI operations.

Provides a centralized console instance configured for the current environment.
"""

import os
import sys

from rich.console import Console


def is_testing_environment() -> bool:
    """
    Detect if we're running in a testing environment.

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
    """
    Get a console instance configured for the current environment.

    Returns a console with colors disabled during testing or when
    output is not going to a terminal.

    Special handling for Click's CliRunner: detects when running under
    CliRunner and uses dynamic sys.stdout wrapper so Click can redirect output.
    """
    import sys

    # Check if we're in pytest/testing mode
    in_pytest = any(
        [
            "PYTEST_CURRENT_TEST" in os.environ,
            "pytest" in sys.modules,
            "_pytest" in [m.split(".")[0] for m in sys.modules.keys()],
        ]
    )

    if in_pytest:
        # In testing, don't bind to sys.stdout at creation time
        # Instead use sys.__stdout__ which is the original stdout
        # Click's CliRunner will capture from the real stdout stream
        return Console(force_terminal=False, no_color=True, width=80)
    else:
        return Console()
