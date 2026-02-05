"""Service for fetching milestones from GitHub API."""

from datetime import datetime

from structlog import get_logger

from roadmap.adapters.sync.backends.github_client import GitHubClientWrapper
from roadmap.common.logging import log_error_with_context
from roadmap.core.models.sync_models import SyncMilestone

logger = get_logger()


class GitHubMilestoneFetchService:
    """Handles fetching milestones from GitHub API."""

    def __init__(
        self,
        github_client: GitHubClientWrapper,
        config: dict,
    ):
        """Initialize milestone fetch service.

        Args:
            github_client: GitHubClientWrapper for API access
            config: Configuration dict with 'owner', 'repo'
        """
        self.github_client = github_client
        self.config = config

    def get_milestones(self, state: str = "all") -> dict[str, SyncMilestone]:
        """Fetch all milestones from GitHub.

        Args:
            state: Milestone state filter ('open', 'closed', 'all')

        Returns:
            Dict mapping milestone numbers (as strings) to SyncMilestone objects,
            or empty dict if fetch fails.
        """
        if not self.github_client:
            logger.warning("github_milestone_fetch_no_client")
            return {}

        owner = self.config.get("owner")
        repo = self.config.get("repo")

        if not owner or not repo:
            logger.warning(
                "github_milestone_fetch_missing_config", owner=owner, repo=repo
            )
            return {}

        try:
            logger.debug(
                "github_milestone_fetch_start",
                owner=owner,
                repo=repo,
                state=state,
            )

            # Get milestones using GitHub API
            # Import handler and create with proper session
            import requests

            from roadmap.adapters.github.handlers.milestones import MilestoneHandler

            # Create a requests session with authentication
            session = requests.Session()
            token = self.config.get("token")
            if token:
                session.headers.update(
                    {
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "roadmap-cli/1.0",
                    }
                )

            milestone_handler = MilestoneHandler(
                session=session,
                owner=owner,
                repo=repo,
            )

            milestones_data = milestone_handler.get_milestones(state=state)

            logger.info(
                "github_milestones_fetched",
                owner=owner,
                repo=repo,
                count=len(milestones_data),
            )

            # Convert each GitHub milestone to SyncMilestone
            result = {}
            failed_conversions = 0
            for milestone_dict in milestones_data:
                try:
                    sync_milestone = self._dict_to_sync_milestone(milestone_dict)
                    milestone_number = str(milestone_dict.get("number", ""))
                    result[milestone_number] = sync_milestone
                except Exception as e:
                    failed_conversions += 1
                    milestone_number = (
                        milestone_dict.get("number")
                        if isinstance(milestone_dict, dict)
                        else "unknown"
                    )
                    log_error_with_context(
                        e,
                        operation="convert_github_milestone_to_sync",
                        entity_type="Milestone",
                        entity_id=str(milestone_number),
                        additional_context={
                            "owner": owner,
                            "repo": repo,
                            "total_milestones": len(milestones_data),
                        },
                        include_traceback=False,
                    )

            if failed_conversions > 0:
                logger.warning(
                    "github_milestone_conversions_failed",
                    owner=owner,
                    repo=repo,
                    total=len(milestones_data),
                    failed=failed_conversions,
                    successful=len(result),
                )

            return result

        except Exception as e:
            log_error_with_context(
                e,
                operation="fetch_github_milestones",
                entity_type="Milestone",
                additional_context={"owner": owner, "repo": repo, "state": state},
                include_traceback=True,
            )
            return {}

    def _dict_to_sync_milestone(self, milestone_dict: dict) -> SyncMilestone:
        """Convert GitHub milestone dict to SyncMilestone.

        Args:
            milestone_dict: GitHub API milestone response

        Returns:
            SyncMilestone instance

        Raises:
            ValueError: If required fields are missing
        """
        milestone_number = milestone_dict.get("number")
        if not milestone_number:
            raise ValueError("GitHub milestone missing 'number' field")

        title = milestone_dict.get("title")
        if not title:
            raise ValueError(f"GitHub milestone {milestone_number} missing 'title'")

        # Parse state (GitHub uses "open", "closed")
        state = milestone_dict.get("state", "open")

        # Parse due date
        due_date = None
        due_on_str = milestone_dict.get("due_on")
        if due_on_str:
            try:
                # GitHub returns ISO 8601 format with Z suffix
                due_date = datetime.fromisoformat(due_on_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                logger.debug(
                    "github_milestone_due_date_parse_failed",
                    milestone_number=milestone_number,
                    due_on_str=due_on_str,
                    error=str(e),
                )

        # Create SyncMilestone
        sync_milestone = SyncMilestone(
            id=f"gh_milestone_{milestone_number}",
            name=title,
            status=state,
            headline=milestone_dict.get("description", "")[:100]
            if milestone_dict.get("description")
            else None,
            due_date=due_date,
            backend_name="github",
            backend_id=milestone_number,
            remote_ids={"github": milestone_number},
            raw_response=milestone_dict,
            metadata={
                "open_issues": milestone_dict.get("open_issues", 0),
                "closed_issues": milestone_dict.get("closed_issues", 0),
                "created_at": milestone_dict.get("created_at"),
                "updated_at": milestone_dict.get("updated_at"),
            },
        )

        return sync_milestone
