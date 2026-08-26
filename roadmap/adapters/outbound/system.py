"""Adapters for local process identity and time."""

from datetime import UTC, datetime

from roadmap.application.ports import LocalGitPort
from roadmap.domain.types import Timestamp


class SystemClock:
    def now(self) -> Timestamp:
        return Timestamp(datetime.now(UTC))


class ConfiguredCurrentIdentity:
    def __init__(self, configured_name: str | None, local_git: LocalGitPort):
        git_name, _git_email = local_git.user_identity()
        self._identity = configured_name or git_name

    def current_identity(self) -> str | None:
        return self._identity


class LocalAssigneeDirectory:
    """Normalize user-provided names without consulting a remote directory."""

    def canonical_assignee(self, assignee: str) -> str | None:
        normalized = assignee.strip()
        return normalized or None
