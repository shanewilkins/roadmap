"""Roadmap CLI - A command line tool for creating and managing roadmaps."""

__version__ = "0.1.0"

from .core import RoadmapCore
from .credentials import CredentialManager, CredentialManagerError
from .github_client import GitHubAPIError, GitHubClient
from .models import Issue, Milestone, MilestoneStatus, Priority, RoadmapConfig, Status
from .parser import FrontmatterParser, IssueParser, MilestoneParser
from .sync import SyncManager

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
    "SyncManager",
    "CredentialManager",
    "CredentialManagerError",
]
