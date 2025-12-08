"""SQLite-based state management for roadmap CLI application.

This module provides a persistent state management layer using SQLite,
replacing the file-based approach with a proper database backend for
better performance and data integrity.

DEPRECATED: This file is now a backward compatibility facade.
New code should import from `roadmap.adapters.persistence.storage` package instead.
"""

import warnings

# Re-export all public APIs from the storage package
from .storage import (
    DatabaseError,
    StateManager,
    get_state_manager,
    initialize_state_manager,
)

# Emit deprecation warning when this module is imported
warnings.warn(
    "The 'roadmap.adapters.persistence.storage' module is deprecated. "
    "Use 'roadmap.adapters.persistence.storage' package directly instead. "
    "This module will be removed in v1.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "DatabaseError",
    "StateManager",
    "get_state_manager",
    "initialize_state_manager",
]
