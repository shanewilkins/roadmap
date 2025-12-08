"""
Exception Definitions and Error Enums for Roadmap

DEPRECATED: This module is maintained for backward compatibility.
Import directly from roadmap.common.errors package instead.

Example:
    from roadmap.common.errors import RoadmapError, ValidationError
"""

import warnings

# Re-export all error classes from the errors package for backward compatibility
from roadmap.common.errors import *  # noqa: F401, F403

# Emit deprecation warning when this module is imported
warnings.warn(
    "The 'roadmap.common.errors' module is deprecated. "
    "Use 'roadmap.common.errors' package directly instead. "
    "This module will be removed in v1.0.0.",
    DeprecationWarning,
    stacklevel=2,
)
