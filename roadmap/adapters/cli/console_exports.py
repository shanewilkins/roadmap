"""Utility functions for CLI operations.

This module re-exports core utilities from roadmap.common to maintain
backward compatibility with existing CLI code.
"""

# Re-export console utilities from common module to avoid duplication
from roadmap.common.console import get_console, is_testing_environment

__all__ = ["get_console", "is_testing_environment"]
