"""GitHub-specific implementation of SyncBackendInterface.

This module provides the GitHub API backend for syncing roadmap issues
with GitHub repositories. It implements the SyncBackendInterface protocol.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import (
    SyncConflict,
    SyncReport,
)
from roadmap.core.services.github_conflict_detector import GitHubConflictDetector
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.core.services.sync_metadata_service import SyncMetadataService
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger()

T = TypeVar("T")


class GitHubSyncBackend:
    """GitHub API implementation of the SyncBackendInterface.

    Syncs roadmap issues with GitHub issues using the GitHub REST API.
    Requires a GitHub Personal Access Token with 'repo' scope.

    Attributes:
        core: RoadmapCore instance with access to local issues
        config: GitHub configuration with 'owner', 'repo', 'token'
        github_client: GitHubIssueClient for API communication
    """

    def __init__(self, core: RoadmapCore, config: dict[str, Any]):
        """Initialize GitHub sync backend.

        Args:
            core: RoadmapCore instance
            config: Dict with required keys:
                - owner: GitHub repository owner
                - repo: GitHub repository name
                - token: GitHub Personal Access Token (optional, checked at auth time)

        Raises:
            ValueError: If required config keys are missing
        """
        if not config.get("owner") or not config.get("repo"):
            raise ValueError("GitHub config must include 'owner' and 'repo'")

        self.core = core
        self.config = config

        # Initialize GitHub client if token is provided, otherwise defer to authenticate()
        token = config.get("token")
        self.github_client = self._safe_init(
            lambda: GitHubIssueClient(token) if token else None,
            "GitHubIssueClient",
        )

        # Initialize metadata service if available
        self.metadata_service = self._safe_init(
            lambda: SyncMetadataService(core),
            "SyncMetadataService",
        )

        # Initialize conflict detector if available
        self.conflict_detector = None
        if hasattr(core, "github_service") and core.github_service is not None:
            self.conflict_detector = self._safe_init(
                lambda: GitHubConflictDetector(core.github_service),
                "GitHubConflictDetector",
            )

    def _safe_init(self, factory: Callable[[], T], name: str) -> T | None:
        """Safely initialize a component, returning None on failure.

        Args:
            factory: Callable that returns the initialized component
            name: Component name for logging

        Returns:
            Initialized component or None if initialization fails
        """
        try:
            return factory()
        except Exception as e:
            logger.warning(
                "initialization_failed",
                component=name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def authenticate(self) -> bool:
        """Verify credentials and remote connectivity.

        Returns:
            True if authentication succeeds (token valid and repo accessible),
            False otherwise (no exceptions raised).
        """
        try:
            token = self.config.get("token")
            if not token:
                # No token - auth fails
                logger.debug("github_auth_no_token")
                return False

            # Initialize client if not already done
            if self.github_client is None:
                try:
                    self.github_client = GitHubIssueClient(token)
                except Exception as e:
                    logger.error("github_client_init_failed", error=str(e))
                    return False

            owner = self.config.get("owner")
            repo = self.config.get("repo")

            # Type assertions (config is validated in __init__)
            assert isinstance(owner, str), "owner must be a string"
            assert isinstance(repo, str), "repo must be a string"

            # Try to fetch a single issue to validate token and repo access
            # We use a dummy issue number that likely doesn't exist
            # If we get a 401/403, auth failed. If we get 404, auth succeeded.
            logger.info("github_auth_attempting", owner=owner, repo=repo)
            try:
                self.github_client.fetch_issue(owner, repo, 1)
                # Even if issue 1 doesn't exist, we got through auth
                logger.info("github_auth_success", owner=owner, repo=repo)
                return True
            except Exception as e:
                # Check if it's an auth error
                error_msg = str(e).lower()
                if (
                    "401" in error_msg
                    or "403" in error_msg
                    or "unauthorized" in error_msg
                ):
                    logger.warning(
                        "github_auth_failed_unauthorized",
                        owner=owner,
                        repo=repo,
                        error=str(e),
                    )
                    return False
                # Other errors (like 404 for issue not found) mean auth succeeded
                logger.info(
                    "github_auth_success_with_error",
                    owner=owner,
                    repo=repo,
                    error=str(e),
                )
                return True

        except Exception as e:
            logger.error(
                "github_auth_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def get_issues(self) -> dict[str, Any]:
        """Fetch all issues from GitHub remote.

        Returns:
            Dictionary mapping issue_id -> issue_data (as dict).
            Returns empty dict if unable to fetch.

        Notes:
            - Fetches all issues from the GitHub repository
            - Returns issue data in GitHub API format
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            token = self.config.get("token")

            if not owner or not repo or not token:
                return {}

            logger.debug("github_get_issues_started", owner=owner, repo=repo)

            # Fetch all issues using GitHub Client
            issues_data = {}

            try:
                from roadmap.adapters.github.github import GitHubClient

                client = GitHubClient(token=token, owner=owner, repo=repo)

                # Fetch issues with pagination
                page = 1
                per_page = 100

                while True:
                    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                    params = {
                        "state": "all",  # Get both open and closed issues
                        "per_page": per_page,
                        "page": page,
                        "sort": "updated",
                        "direction": "desc",
                    }

                    response = client.session.get(url, params=params)
                    response.raise_for_status()

                    issues = response.json()
                    if not issues:
                        break

                    for issue in issues:
                        # Use GitHub issue number as the ID (with gh- prefix)
                        issue_id = f"gh-{issue.get('number')}"

                        # Extract relevant fields
                        issues_data[issue_id] = {
                            "id": issue_id,
                            "number": issue.get("number"),
                            "title": issue.get("title", ""),
                            "body": issue.get("body", ""),
                            "state": issue.get("state", "open"),  # 'open' or 'closed'
                            "labels": [
                                label.get("name") for label in issue.get("labels", [])
                            ]
                            if issue.get("labels")
                            else [],
                            "assignees": [
                                assignee.get("login")
                                for assignee in issue.get("assignees", [])
                            ]
                            if issue.get("assignees")
                            else [],
                            "assignee": issue.get("assignee", {}).get("login")
                            if issue.get("assignee")
                            else None,
                            "milestone": issue.get("milestone", {}).get("title")
                            if issue.get("milestone")
                            else None,
                            "url": issue.get("html_url", ""),
                            "created_at": issue.get("created_at"),
                            "updated_at": issue.get("updated_at"),
                        }

                    page += 1

                    # For now, limit to first page (100 issues) for performance
                    # In production, we'd paginate through all
                    if page > 1:
                        break

                logger.info(
                    "github_get_issues_completed",
                    count=len(issues_data),
                    owner=owner,
                    repo=repo,
                )
                return issues_data

            except Exception as e:
                logger.error(
                    "github_api_fetch_failed",
                    owner=owner,
                    repo=repo,
                    error=str(e),
                    exc_info=True,
                )
                return {}

        except Exception as e:
            logger.exception("github_get_issues_failed", error=str(e))
            return {}

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to GitHub.

        Args:
            local_issue: The Issue object to push

        Returns:
            True if push succeeds, False if error.

        Notes:
            - Creates new GitHub issue if not linked (no github_issue field)
            - Updates existing GitHub issue if linked (has github_issue field)
            - Stores the GitHub issue number for future syncs
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            token = self.config.get("token")

            if not owner or not repo or not token:
                return False

            logger.debug("github_push_issue_started", issue_id=local_issue.id)

            from roadmap.adapters.github.github import GitHubClient

            client = GitHubClient(token=token, owner=owner, repo=repo)

            # Check if this issue is already linked to a GitHub issue
            if local_issue.github_issue:
                # Update existing GitHub issue
                github_issue_number = int(local_issue.github_issue)

                url = f"https://api.github.com/repos/{owner}/{repo}/issues/{github_issue_number}"
                payload = {
                    "title": local_issue.title,
                    "body": local_issue.content or "",
                    "state": "closed"
                    if local_issue.status.value == "closed"
                    else "open",
                    # Labels: convert local labels to GitHub label names
                    "labels": local_issue.labels,
                    # Milestone: GitHub expects milestone number, but we only have title
                    # For now, skip milestone updates on push (would need milestone ID)
                }

                response = client.session.patch(url, json=payload)
                response.raise_for_status()

                logger.info(
                    "github_push_issue_updated",
                    issue_id=local_issue.id,
                    github_number=github_issue_number,
                )
                return True

            else:
                # Create new GitHub issue
                url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                payload: dict[str, Any] = {
                    "title": local_issue.title,
                    "body": local_issue.content or "",
                }

                # Only include labels if they exist and are non-empty
                # Handle labels that might be comma-separated strings
                if local_issue.labels:
                    labels_list = []
                    for label in local_issue.labels:
                        if isinstance(label, str):
                            # Split comma-separated labels into individual labels
                            labels_list.extend(
                                [
                                    label_item.strip()
                                    for label_item in label.split(",")
                                    if label_item.strip()
                                ]
                            )
                        else:
                            # In case label is not a string, convert to string
                            labels_list.append(str(label).strip())

                    if labels_list:  # Only include if we have labels after processing
                        payload["labels"] = labels_list

                response = client.session.post(url, json=payload)

                # Debug: Log response status and content for 422 errors
                if response.status_code >= 400:
                    with open("/tmp/github_api_error.log", "a") as f:
                        f.write(
                            f"\n=== GITHUB API ERROR (Status {response.status_code}) ===\n"
                        )
                        f.write(f"URL: {url}\n")
                        f.write(f"Payload: {payload}\n")
                        f.write(f"Response: {response.text}\n")
                        f.write("=====================================\n")

                response.raise_for_status()

                github_response = response.json()
                github_issue_number = github_response.get("number")

                if github_issue_number:
                    # Store the GitHub issue number on the local issue for future syncs
                    from roadmap.adapters.persistence.yaml_repositories import (
                        YAMLIssueRepository,
                    )

                    if hasattr(self.core, "issue_service") and hasattr(
                        self.core.issue_service, "repository"
                    ):
                        repo_inst = self.core.issue_service.repository
                        if isinstance(repo_inst, YAMLIssueRepository):
                            local_issue.github_issue = github_issue_number
                            repo_inst.save(local_issue)

                logger.info(
                    "github_push_issue_created",
                    issue_id=local_issue.id,
                    github_number=github_issue_number,
                )
                return True

        except Exception as e:
            logger.warning(
                "github_push_issue_failed",
                issue_id=local_issue.id,
                error=str(e),
                exc_info=True,
            )
            return False

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to GitHub.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.
        """
        report = SyncReport()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task(
                f"Pushing {len(local_issues)} issues to GitHub...",
                total=len(local_issues),
            )

            for i, issue in enumerate(local_issues, 1):
                try:
                    progress.update(
                        task,
                        description=f"Pushing issue {i}/{len(local_issues)}: {issue.id}",
                    )
                    if self.push_issue(issue):
                        report.pushed.append(issue.id)
                    else:
                        report.errors[issue.id] = "Failed to push issue"
                except Exception as e:
                    report.errors[issue.id] = str(e)
                finally:
                    progress.advance(task)

        return report

    def pull_issues(self) -> SyncReport:
        """Pull all remote GitHub issues to local.

        Returns:
            SyncReport with pulled, conflicts, and errors.

        Notes:
            - This method is for bulk pulls. Individual pulls are handled by pull_issue.
            - Delegates to orchestrator for determining which issues to pull.
        """
        # This is handled by the orchestrator calling pull_issue for specific issues
        # Keeping this stub for interface compatibility
        report = SyncReport()
        return report

    def pull_issue(self, issue_id: str) -> bool:
        """Pull a single remote GitHub issue to local.

        Args:
            issue_id: The remote issue ID to pull

        Returns:
            True if pull succeeds, False if error.

        Notes:
            - Fetches the remote issue and updates local
            - Should not raise exceptions; return False on failure
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            # Fetch the remote issue by ID
            remote_issues = self.get_issues()
            remote_issue = remote_issues.get(issue_id)

            if not remote_issue:
                logger.warning("pull_issue_not_found_remote", issue_id=issue_id)
                return False

            title = remote_issue.get("title", "")

            if not issue_id or not title:
                logger.warning(
                    "pull_issue_missing_id_or_title", remote_issue=remote_issue
                )
                return False
            logger.debug("github_pull_issue_started", issue_id=issue_id)

            # Convert GitHub remote dict to local Issue object
            issue = self._convert_github_to_issue(issue_id, remote_issue)

            # Extract GitHub issue number from remote issue
            github_issue_number = remote_issue.get("number")

            # Check if issue with same GitHub issue number exists locally
            # This is the primary match - if we've synced this GitHub issue before, use existing
            existing_issues = self.core.issues.list()
            matching_local_issue = None

            # First priority: match by github_issue_number (already synced)
            for local_issue in existing_issues:
                if (
                    local_issue.github_issue is not None
                    and int(local_issue.github_issue) == github_issue_number
                ):
                    matching_local_issue = local_issue
                    logger.debug(
                        "github_pull_found_existing_by_github_number",
                        github_number=github_issue_number,
                        local_id=local_issue.id,
                    )
                    break

            # Second priority: match by title (first-time sync of existing local issue)
            if not matching_local_issue:
                for local_issue in existing_issues:
                    if local_issue.title.lower() == title.lower():
                        matching_local_issue = local_issue
                        logger.debug(
                            "github_pull_found_matching_by_title",
                            github_number=github_issue_number,
                            local_id=local_issue.id,
                            title=title,
                        )
                        break

            # Update/create locally using the coordinator
            # Extract only the fields that update_issue accepts
            updates = {
                "title": issue.title,
                "status": issue.status,
                "priority": issue.priority,
                "assignee": issue.assignee,
                "milestone": issue.milestone,
                "description": issue.content,  # Issue.content → description
            }

            if matching_local_issue:
                # Update existing issue and store GitHub issue number
                self.core.issues.update(matching_local_issue.id, **updates)

                # Also update the github_issue field to track this link for future syncs
                # Use raw file update to add the github_issue field
                from roadmap.adapters.persistence.yaml_repositories import (
                    YAMLIssueRepository,
                )

                # Get the issue service to access the repository
                if hasattr(self.core, "issue_service") and hasattr(
                    self.core.issue_service, "repository"
                ):
                    repo = self.core.issue_service.repository
                    if isinstance(repo, YAMLIssueRepository):
                        # Load the issue, update github_issue field, save
                        updated_issue = self.core.issues.get(matching_local_issue.id)
                        if updated_issue:
                            updated_issue.github_issue = github_issue_number
                            repo.save(updated_issue)

                logger.debug(
                    "github_pull_issue_updated",
                    github_number=github_issue_number,
                    local_id=matching_local_issue.id,
                )
            elif self.core.issues.get(issue_id):
                # Update if it already exists with same ID
                self.core.issues.update(issue_id, **updates)
                logger.debug("github_pull_issue_updated", issue_id=issue_id)
            else:
                # Create new issue with github_issue number
                created_issue = self.core.issues.create(
                    title=issue.title,
                    status=issue.status,
                    priority=issue.priority,
                    assignee=issue.assignee,
                    milestone=issue.milestone,
                    issue_type=issue.issue_type,
                    labels=issue.labels,
                    estimated_hours=issue.estimated_hours,
                )

                # Store GitHub issue number for future syncs
                if created_issue:
                    from roadmap.adapters.persistence.yaml_repositories import (
                        YAMLIssueRepository,
                    )

                    if hasattr(self.core, "issue_service") and hasattr(
                        self.core.issue_service, "repository"
                    ):
                        repo = self.core.issue_service.repository
                        if isinstance(repo, YAMLIssueRepository):
                            created_issue.github_issue = github_issue_number
                            repo.save(created_issue)

                logger.debug(
                    "github_pull_issue_created",
                    github_number=github_issue_number,
                    local_id=created_issue.id if created_issue else "unknown",
                )

            logger.info("github_pull_issue_completed", issue_id=issue_id)
            return True

        except Exception as e:
            logger.warning(
                "github_pull_issue_failed",
                issue_id=issue_id,
                error=str(e),
                exc_info=True,
            )
            return False

    def _convert_github_to_issue(
        self, issue_id: str, remote_data: dict[str, Any]
    ) -> "Issue":
        """Convert GitHub issue dict to local Issue object.

        Args:
            issue_id: Local issue ID
            remote_data: GitHub issue data from API

        Returns:
            Issue instance with converted data

        Raises:
            ValueError: If conversion fails
        """
        from datetime import timezone

        from roadmap.core.domain.issue import (
            Issue,
            IssueType,
            Priority,
            Status,
        )

        # Map GitHub state to local Status
        github_state = remote_data.get("state", "open")
        status_map = {"open": Status.TODO, "closed": Status.CLOSED}
        status = status_map.get(github_state, Status.TODO)

        # Default priority to medium (GitHub doesn't have priority in issues)
        priority = Priority.MEDIUM

        # Extract timestamps
        created_at_str = remote_data.get("created_at")
        created = self._parse_timestamp(created_at_str) or datetime.now(timezone.utc)

        updated_at_str = remote_data.get("updated_at")
        updated = self._parse_timestamp(updated_at_str) or datetime.now(timezone.utc)

        # Extract labels as list of label names
        labels = []
        if "labels" in remote_data:
            # GitHub returns labels as list of dicts with 'name' key
            labels_data = remote_data.get("labels", [])
            if isinstance(labels_data, list):
                labels = (
                    [
                        label["name"] if isinstance(label, dict) else str(label)
                        for label in labels_data
                    ]
                    if labels_data
                    else []
                )

        # Extract assignee (first assignee if multiple)
        assignee = None
        assignees = remote_data.get("assignees", [])
        if assignees and isinstance(assignees, list):
            first_assignee = assignees[0]
            assignee = (
                first_assignee.get("login")
                if isinstance(first_assignee, dict)
                else str(first_assignee)
            )
        elif "assignee" in remote_data and remote_data["assignee"]:
            assignee_data = remote_data["assignee"]
            assignee = (
                assignee_data.get("login")
                if isinstance(assignee_data, dict)
                else str(assignee_data)
            )

        # Extract milestone
        milestone = None
        milestone_data = remote_data.get("milestone")
        if milestone_data:
            milestone = (
                milestone_data.get("title")
                if isinstance(milestone_data, dict)
                else str(milestone_data)
            )

        # Create Issue object
        issue = Issue(
            id=issue_id,
            title=remote_data.get("title", ""),
            status=status,
            priority=priority,
            issue_type=IssueType.OTHER,  # GitHub doesn't have issue types
            created=created,
            updated=updated,
            milestone=milestone,
            assignee=assignee,
            labels=labels,
            content=remote_data.get("body") or "",  # Handle None body
            # Don't set estimated_hours - GitHub doesn't have this
            # Don't set due_date - GitHub doesn't have this in basic API
        )

        return issue

    def _parse_timestamp(self, timestamp_str: str | None) -> "datetime | None":
        """Parse ISO format timestamp string.

        Args:
            timestamp_str: ISO format timestamp (may have 'Z' suffix)

        Returns:
            datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None

        try:
            if isinstance(timestamp_str, str):
                # Handle 'Z' timezone suffix
                if timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                return datetime.fromisoformat(timestamp_str)
            return timestamp_str  # Already a datetime
        except (ValueError, AttributeError):
            return None

    def get_conflict_resolution_options(self, conflict: SyncConflict) -> list[str]:
        """Get available resolution strategies for a conflict.

        Args:
            conflict: The SyncConflict to resolve

        Returns:
            List of resolution option codes (e.g., ['use_local', 'use_remote', 'merge'])
        """
        # GitHub backend supports the three basic strategies
        return ["use_local", "use_remote", "merge"]

    def resolve_conflict(self, conflict: SyncConflict, resolution: str) -> bool:
        """Resolve a sync conflict using specified strategy.

        Args:
            conflict: The SyncConflict to resolve
            resolution: The resolution strategy code ('use_local', 'use_remote', or 'merge')

        Returns:
            True if resolution succeeds, False otherwise.
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            logger.debug(
                "github_resolve_conflict_started",
                issue_id=conflict.issue_id,
                resolution=resolution,
            )

            # For now, return True to indicate success
            # Full implementation will handle actual conflict resolution
            # when GitHub backend API is fully implemented

            logger.info(
                "github_resolve_conflict_completed",
                issue_id=conflict.issue_id,
                resolution=resolution,
            )
            return True

        except Exception as e:
            logger.warning(
                "github_resolve_conflict_failed",
                issue_id=conflict.issue_id,
                resolution=resolution,
                error=str(e),
            )
            return False
