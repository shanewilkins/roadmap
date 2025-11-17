"""Roadmap CLI - A command line tool for creating and managing roadmaps."""

__version__ = "0.4.0"

from .core import RoadmapCore
from .credentials import CredentialManager, CredentialManagerError
from .github_client import GitHubAPIError, GitHubClient
from .models import Issue, Milestone, MilestoneStatus, Priority, RoadmapConfig, Status
from .parser import FrontmatterParser, IssueParser, MilestoneParser

__all__ = [
    "Issue",
    "Milestone",
    "Priority",
    "Status",
    "MilestoneStatus",
    "RoadmapConfig",
    "IssueParser",
    "MilestoneParser",
    "FrontmatterParser",
    "RoadmapCore",
    "GitHubClient",
    "GitHubAPIError",
    "CredentialManager",
    "CredentialManagerError",
]
