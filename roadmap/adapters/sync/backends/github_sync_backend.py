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
from roadmap.core.models.sync_models import (
    SyncIssue,
    SyncMilestone,
    SyncProject,
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

        # Initialize remote link repository if available
        # This enables fast database lookups during sync operations
        self.remote_link_repo = None
        if (
            hasattr(core, "db")
            and core.db is not None
            and hasattr(core.db, "remote_links")
        ):
            self.remote_link_repo = core.db.remote_links

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
        except (ImportError, AttributeError) as e:
            logger.warning(
                "initialization_failed",
                component=name,
                error=str(e),
                error_type=type(e).__name__,
                suggested_action="check_dependencies",
            )
            return None
        except Exception as e:
            logger.warning(
                "initialization_failed",
                component=name,
                error=str(e),
                error_type=type(e).__name__,
                error_classification="unknown_error",
            )
            return None

    def get_backend_name(self) -> str:
        """Get the canonical name of this backend.

        Returns:
            'github' - used as key in Issue.remote_ids dict
        """
        return "github"

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
                except (ImportError, TypeError) as e:
                    logger.error(
                        "github_client_init_failed",
                        error_type=type(e).__name__,
                        error=str(e),
                        suggested_action="check_dependencies",
                    )
                    return False
                except Exception as e:
                    logger.error(
                        "github_client_init_failed",
                        error_type=type(e).__name__,
                        error=str(e),
                        error_classification="initialization_error",
                    )
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
                error_type=type(e).__name__,
                error=str(e),
                error_classification="authentication_error",
                suggested_action="check_network",
            )
            return False

    def get_issues(self) -> dict[str, SyncIssue]:
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

                    # Continue fetching all pages (no limit for production)
                    # Pagination ensures we get all issues regardless of count

                logger.info(
                    "github_get_issues_completed",
                    count=len(issues_data),
                    owner=owner,
                    repo=repo,
                )
                # Convert dict representations to SyncIssue objects
                return {
                    issue_id: self._dict_to_sync_issue(issue_dict)
                    for issue_id, issue_dict in issues_data.items()
                }

            except (ConnectionError, TimeoutError) as e:
                logger.error(
                    "github_api_fetch_failed",
                    operation="fetch_issues",
                    owner=owner,
                    repo=repo,
                    error_type=type(e).__name__,
                    error=str(e),
                    is_recoverable=True,
                    suggested_action="retry_after_delay",
                )
                return {}
            except Exception as e:
                logger.error(
                    "github_api_fetch_failed",
                    operation="fetch_issues",
                    owner=owner,
                    repo=repo,
                    error_type=type(e).__name__,
                    error=str(e),
                    is_recoverable=False,
                    suggested_action="check_configuration",
                )
                return {}

        except Exception as e:
            logger.error(
                "github_get_issues_failed",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_configuration",
            )
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
                payload: dict[str, Any] = {
                    "title": local_issue.title,
                    "body": local_issue.content or "",
                    "state": "closed"
                    if local_issue.status.value == "closed"
                    else "open",
                    # Milestone: GitHub expects milestone number, but we only have title
                    # For now, skip milestone updates on push (would need milestone ID)
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

                response = client.session.patch(url, json=payload)
                response.raise_for_status()

                # NOTE: Linking via remote_ids will be handled by sync state manager
                # We don't save the issue file here to preserve idempotency and avoid
                # unnecessary file modifications with updated timestamps

                logger.info(
                    "github_push_issue_updated",
                    issue_id=local_issue.id,
                    github_number=github_issue_number,
                )
                return True

            else:
                # Create new GitHub issue
                # But first, check if an issue with the same title already exists on GitHub
                # to prevent duplicates
                all_remote_issues = self.get_issues()
                duplicate_issue = None
                for remote_issue in all_remote_issues.values():
                    if remote_issue.title.lower() == local_issue.title.lower():
                        duplicate_issue = remote_issue
                        logger.warning(
                            "github_push_issue_found_duplicate",
                            issue_id=local_issue.id,
                            github_number=remote_issue.backend_id,
                            title=local_issue.title,
                        )
                        break

                # If we found a duplicate, link it instead of creating a new one
                if duplicate_issue and duplicate_issue.backend_id:
                    github_issue_number = duplicate_issue.backend_id
                    # NOTE: Linking will be handled by sync state manager, not by file save
                    logger.info(
                        "github_duplicate_issue_linked",
                        issue_id=local_issue.id,
                        github_number=github_issue_number,
                    )
                    return True

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

                response.raise_for_status()

                github_response = response.json()
                github_issue_number = github_response.get("number")

                # NOTE: Linking via remote_ids will be handled by sync state manager
                # We don't save the issue file here to preserve idempotency
                logger.info(
                    "github_push_issue_created",
                    issue_id=local_issue.id,
                    github_number=github_issue_number,
                )
                return True

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "github_push_issue_failed",
                issue_id=local_issue.id,
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="retry_after_delay",
            )
            return False
        except Exception as e:
            logger.warning(
                "github_push_issue_failed",
                issue_id=local_issue.id,
                error_type=type(e).__name__,
                error=str(e),
                error_classification="sync_error",
            )
            return False

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to GitHub.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        report = SyncReport()

        if not local_issues:
            return report

        # Use thread pool for parallel pushing (max 5 concurrent API calls)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            "[progress.percentage]{task.percentage:>3.1f}%",
        ) as progress:
            task = progress.add_task(
                f"[cyan]📤 Pushing 0/{len(local_issues)} issues...",
                total=len(local_issues),
            )

            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all push tasks
                futures = {
                    executor.submit(self.push_issue, issue): issue
                    for issue in local_issues
                }

                # Process results as they complete
                for future in as_completed(futures):
                    issue = futures[future]
                    try:
                        if future.result():
                            report.pushed.append(issue.id)
                            status = "✓"
                        else:
                            report.errors[issue.id] = "Failed to push issue"
                            status = "✗"
                    except Exception as e:
                        report.errors[issue.id] = str(e)
                        status = "✗"
                    finally:
                        progress.update(
                            task,
                            description=f"[cyan]📤 Pushing {len(report.pushed)}/{len(local_issues)} issues... {status} {issue.id[:8]}",
                        )
                        progress.advance(task)

        return report

    def pull_issues(self, issue_ids: list[str]) -> SyncReport:
        """Pull specified remote GitHub issues to local.

        Args:
            issue_ids: List of remote issue IDs to pull

        Returns:
            SyncReport with pulled, conflicts, and errors.

        Notes:
            - Each ID should correspond to a remote issue
            - Updates or creates local files as needed
            - Uses parallel execution with thread pool for performance
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from structlog import get_logger

        logger = get_logger()
        report = SyncReport()

        if not issue_ids:
            return report

        try:
            logger.info(
                "pull_issues_starting",
                issue_count=len(issue_ids),
            )

            successful_pulls = []
            failed_pulls = {}

            # Use thread pool for parallel pulling (max 5 concurrent API calls)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                "[progress.percentage]{task.percentage:>3.1f}%",
            ) as progress:
                task = progress.add_task(
                    f"[magenta]📥 Pulling 0/{len(issue_ids)} issues...",
                    total=len(issue_ids),
                )

                with ThreadPoolExecutor(max_workers=5) as executor:
                    # Submit all pull tasks
                    futures = {
                        executor.submit(self.pull_issue, issue_id): issue_id
                        for issue_id in issue_ids
                    }

                    # Process results as they complete
                    for future in as_completed(futures):
                        issue_id = futures[future]
                        try:
                            success = future.result()
                            if success:
                                successful_pulls.append(issue_id)
                                status = "✓"
                            else:
                                failed_pulls[issue_id] = "Pull failed"
                                status = "✗"
                        except Exception as e:
                            logger.warning(
                                "pull_issue_exception",
                                issue_id=issue_id,
                                error=str(e),
                            )
                            failed_pulls[issue_id] = str(e)
                            status = "✗"
                        finally:
                            progress.update(
                                task,
                                description=f"[magenta]📥 Pulling {len(successful_pulls)}/{len(issue_ids)} issues... {status} {issue_id}",
                            )
                            progress.advance(task)

            report.pulled = successful_pulls
            report.errors = failed_pulls

            logger.info(
                "pull_issues_complete",
                successful=len(successful_pulls),
                failed=len(failed_pulls),
            )

            return report

        except Exception as e:
            logger.error(
                "pull_issues_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            report.error = f"Failed to pull issues: {str(e)}"
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

            title = remote_issue.title or ""

            if not issue_id or not title:
                logger.warning(
                    "pull_issue_missing_id_or_title", remote_issue=remote_issue
                )
                return False
            logger.debug("github_pull_issue_started", issue_id=issue_id)

            # Convert remote SyncIssue to local Issue object
            issue = self._convert_sync_to_issue(issue_id, remote_issue)

            # Extract GitHub issue number from remote issue
            github_issue_number = remote_issue.backend_id

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
                        # Load the issue, update github_issue field and remote_ids, save
                        updated_issue = self.core.issues.get(matching_local_issue.id)
                        if updated_issue:
                            updated_issue.github_issue = github_issue_number
                            # Auto-link: set remote_ids for this backend
                            if github_issue_number is not None:
                                if not updated_issue.remote_ids:
                                    updated_issue.remote_ids = {}
                                updated_issue.remote_ids["github"] = github_issue_number
                            repo.save(updated_issue)
                            logger.debug(
                                "github_auto_linked_on_pull",
                                issue_id=updated_issue.id,
                                github_number=github_issue_number,
                            )
                            # Update sync baseline state for successfully pulled issue
                            try:
                                from roadmap.core.services.sync_state_manager import (
                                    SyncStateManager,
                                )

                                state_manager = SyncStateManager(self.core.roadmap_dir)
                                state_manager.save_base_state(
                                    updated_issue, remote_version=True
                                )
                                logger.debug(
                                    "pulled_issue_baseline_updated",
                                    issue_id=updated_issue.id,
                                )
                            except Exception as e:
                                logger.warning(
                                    "pulled_issue_baseline_update_failed",
                                    issue_id=matching_local_issue.id,
                                    error=str(e),
                                )

                logger.debug(
                    "github_pull_issue_updated",
                    github_number=github_issue_number,
                    local_id=matching_local_issue.id,
                )
            elif self.core.issues.get(issue_id):
                # Update if it already exists with same ID
                self.core.issues.update(issue_id, **updates)

                # Auto-link: set remote_ids for this backend
                from roadmap.adapters.persistence.yaml_repositories import (
                    YAMLIssueRepository,
                )

                if hasattr(self.core, "issue_service") and hasattr(
                    self.core.issue_service, "repository"
                ):
                    repo = self.core.issue_service.repository
                    if isinstance(repo, YAMLIssueRepository):
                        # Load the issue and update remote_ids
                        updated_issue = self.core.issues.get(issue_id)
                        if updated_issue:
                            if github_issue_number is not None:
                                if not updated_issue.remote_ids:
                                    updated_issue.remote_ids = {}
                                updated_issue.remote_ids["github"] = github_issue_number
                            repo.save(updated_issue)
                            logger.debug(
                                "github_auto_linked_on_pull",
                                issue_id=updated_issue.id,
                                github_number=github_issue_number,
                            )
                            # Update sync baseline state for successfully pulled issue
                            try:
                                from roadmap.core.services.sync_state_manager import (
                                    SyncStateManager,
                                )

                                state_manager = SyncStateManager(self.core.roadmap_dir)
                                state_manager.save_base_state(
                                    updated_issue, remote_version=True
                                )
                                logger.debug(
                                    "pulled_issue_baseline_updated",
                                    issue_id=updated_issue.id,
                                )
                            except Exception as e:
                                logger.warning(
                                    "pulled_issue_baseline_update_failed",
                                    issue_id=issue_id,
                                    error=str(e),
                                )

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
                            # Auto-link: set remote_ids for this backend
                            if github_issue_number is not None:
                                if not created_issue.remote_ids:
                                    created_issue.remote_ids = {}
                                created_issue.remote_ids["github"] = github_issue_number
                            repo.save(created_issue)
                            logger.debug(
                                "github_auto_linked_on_pull",
                                issue_id=created_issue.id,
                                github_number=github_issue_number,
                            )
                            # Update sync baseline state for successfully pulled issue
                            try:
                                from roadmap.core.services.sync_state_manager import (
                                    SyncStateManager,
                                )

                                state_manager = SyncStateManager(self.core.roadmap_dir)
                                state_manager.save_base_state(
                                    created_issue, remote_version=True
                                )
                                logger.debug(
                                    "pulled_issue_baseline_updated",
                                    issue_id=created_issue.id,
                                )
                            except Exception as e:
                                logger.warning(
                                    "pulled_issue_baseline_update_failed",
                                    issue_id=created_issue.id,
                                    error=str(e),
                                )

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

    def _convert_sync_to_issue(self, issue_id: str, sync_issue: SyncIssue) -> "Issue":
        """Convert SyncIssue to local Issue object.

        Args:
            issue_id: Local issue ID
            sync_issue: SyncIssue with remote data

        Returns:
            Issue instance with converted data

        Raises:
            ValueError: If conversion fails
        """
        from datetime import datetime, timezone

        from roadmap.core.domain.issue import (
            Issue,
            IssueType,
            Priority,
            Status,
        )

        # Map GitHub state to local Status
        github_state = sync_issue.status or "open"
        status_map = {"open": Status.TODO, "closed": Status.CLOSED}
        status = status_map.get(github_state, Status.TODO)

        # Default priority to medium (GitHub doesn't have priority in issues)
        priority = Priority.MEDIUM

        # Extract timestamps - sync_issue already has datetime objects
        created = sync_issue.created_at or datetime.now(timezone.utc)
        updated = sync_issue.updated_at or datetime.now(timezone.utc)

        # Extract labels
        labels = sync_issue.labels or []

        # Extract assignee
        assignee = sync_issue.assignee

        # Extract milestone
        milestone = sync_issue.milestone

        # Get the headline
        content = sync_issue.headline or ""

        # Remote IDs mapping - ensure all values are str | int
        if sync_issue.remote_ids:
            remote_ids: dict[str, str | int] = sync_issue.remote_ids
        else:
            # Ensure backend_id is not None for the remote_ids dict
            remote_ids = (
                {"github": str(sync_issue.backend_id)} if sync_issue.backend_id else {}
            )

        return Issue(
            id=issue_id,
            title=sync_issue.title or "Untitled",
            content=content,
            status=status,
            priority=priority,
            issue_type=IssueType.FEATURE,  # Default to feature
            labels=labels,
            assignee=assignee,
            milestone=milestone,
            created=created,
            updated=updated,
            remote_ids=remote_ids,
        )

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

    def get_milestones(self) -> dict[str, SyncMilestone]:
        """Fetch all milestones from GitHub.

        Currently returns empty dict as detailed milestone fetching is not yet implemented.
        """
        # TODO: Implement full milestone fetching from GitHub API
        return {}

    def get_projects(self) -> dict[str, SyncProject]:
        """Fetch all projects from GitHub.

        Currently returns empty dict as project fetching is not yet implemented.
        GitHub uses classic Project Boards and newer Projects (beta).
        """
        # TODO: Implement GitHub Projects API integration
        return {}

    @staticmethod
    def _dict_to_sync_issue(issue_dict: dict[str, Any]) -> SyncIssue:
        """Convert a raw GitHub API issue dict to SyncIssue.

        Args:
            issue_dict: Dict with issue data from GitHub API

        Returns:
            SyncIssue instance
        """
        issue_id = issue_dict.get("id", issue_dict.get("number", ""))
        return SyncIssue(
            id=str(issue_id),
            title=issue_dict.get("title", ""),
            status=issue_dict.get("state", "open"),
            headline=issue_dict.get("body", ""),
            assignee=issue_dict.get("assignee"),
            milestone=issue_dict.get("milestone"),
            labels=issue_dict.get("labels", []),
            created_at=issue_dict.get("created_at"),
            updated_at=issue_dict.get("updated_at"),
            backend_name="github",
            backend_id=str(issue_dict.get("number", "")),
            remote_ids={"github": str(issue_dict.get("number", ""))},
            raw_response=issue_dict,
        )
