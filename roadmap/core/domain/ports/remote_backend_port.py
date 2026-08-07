"""Port for communicating with remote systems (GitHub, etc)."""

from abc import ABC, abstractmethod

from roadmap.common.result import Result
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.sync_errors import SyncError


class IRemoteBackendPort(ABC):
    """Port for communicating with remote systems (GitHub, etc)."""

    @abstractmethod
    def authenticate(self) -> Result[None, SyncError]:
        """Authenticate with remote backend. Returns Ok(None) or Err."""
        pass

    @abstractmethod
    def get_issues(self) -> Result[dict[str, SyncIssue], SyncError]:
        """Fetch all remote issues. Key is issue ID, value is SyncIssue."""
        pass

    @abstractmethod
    def push_issue(self, issue_id: str, _payload: dict) -> Result[None, SyncError]:
        """Push local issue to remote."""
        pass

    @abstractmethod
    def pull_issue(self, remote_id: str) -> Result[SyncIssue, SyncError]:
        """Pull single remote issue."""
        pass
