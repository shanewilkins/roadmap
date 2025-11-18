"""
Presentation Layer - CLI Interface

This layer handles all command-line interface interaction.
Organized by feature domain for clarity and modularity.

Structure:
- cli/: Command-line interface commands
  - core.py: Main CLI entry point
  - issues/: Issue management commands
  - milestones/: Milestone management commands
  - projects/: Project management commands
  - progress/: Progress display commands
  - data/: Data export commands
  - git/: Git hooks and operations commands
  - comment.py: Comment commands
  - utils.py: CLI utilities

Guidelines:
- Commands should be <200 lines each
- All CLI logic here, not in application or domain
- Commands call services to perform operations
- Depends only on application and shared layers
- No direct database or external system calls
"""
