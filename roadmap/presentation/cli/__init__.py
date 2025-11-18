"""CLI command packages - Organized by feature domain.

Commands are organized into feature-specific subpackages:
- issues/: Issue management (create, list, update, close)
- milestones/: Milestone management (create, list, update)
- projects/: Project management (create, list)
- progress/: Progress display
- data/: Data export and management
- git/: Git hooks and operations

For now, commands are re-exported from the legacy roadmap.cli package
for backward compatibility. Gradually migrating to new structure.
"""

# Re-export all command groups for discovery and registration
from roadmap.presentation.cli import data, git, issues, milestones, progress, projects

# Lazily import main to avoid circular imports
def __getattr__(name):
    if name == "main":
        from roadmap.cli import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["issues", "milestones", "projects", "progress", "data", "git", "main"]
