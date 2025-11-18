"""Git integration module - DEPRECATED.

DEPRECATED: This module is maintained for backward compatibility.
New code should import from roadmap.infrastructure.git instead.

- GitBranch, GitCommit, GitIntegration -> roadmap.infrastructure.git
"""

# Re-export all from infrastructure layer for backward compatibility
from roadmap.infrastructure.git import *  # noqa: F401, F403
from roadmap.infrastructure.git import GitBranch, GitCommit, GitIntegration

__all__ = ["GitBranch", "GitCommit", "GitIntegration"]
