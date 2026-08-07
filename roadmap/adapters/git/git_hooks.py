"""Git hooks and workflow automation for roadmap integration.

This module provides re-exports of hook management and workflow automation
classes for backward compatibility. New code should import from the specific
modules directly:
  - git_hooks_manager.GitHookManager
  - workflow_automation.WorkflowAutomation
"""

from roadmap.adapters.persistence.parser import IssueParser

from .git import GitCommit, GitIntegration
from .git_hooks_manager import GitHookManager
from .workflow_automation import WorkflowAutomation

__all__ = [
    "GitHookManager",
    "WorkflowAutomation",
    "GitIntegration",
    "GitCommit",
    "IssueParser",
]
