"""Service for authenticating with GitHub API."""

from structlog import get_logger

from roadmap.adapters.sync.backends.github_client import GitHubClientWrapper
from roadmap.common.logging import log_error_with_context

logger = get_logger()


class GitHubAuthenticationService:
    """Handles GitHub API authentication and token validation."""

    def __init__(self, config: dict):
        """Initialize authentication service.

        Args:
            config: Configuration dict with 'owner', 'repo', 'token'
        """
        self.config = config
        self.github_client = None

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
                    self.github_client = GitHubClientWrapper(token)
                except (ImportError, TypeError) as e:
                    log_error_with_context(
                        e,
                        operation="initialize_github_client",
                        additional_context={"suggested_action": "check_dependencies"},
                        include_traceback=True,
                    )
                    return False
                except Exception as e:
                    log_error_with_context(
                        e,
                        operation="initialize_github_client",
                        additional_context={
                            "error_classification": "initialization_error"
                        },
                        include_traceback=True,
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
                logger.info("github_auth_successful", owner=owner, repo=repo)
                return True
            except Exception as auth_error:
                if "401" in str(auth_error) or "403" in str(auth_error):
                    log_error_with_context(
                        auth_error,
                        operation="github_authentication",
                        entity_type="Repository",
                        entity_id=f"{owner}/{repo}",
                        additional_context={
                            "suggested_action": "check_token_validity_and_permissions"
                        },
                        include_traceback=False,
                    )
                else:
                    logger.info(
                        "github_auth_successful_by_exception",
                        error=str(auth_error),
                        owner=owner,
                        repo=repo,
                    )
                    return True
                return False

        except Exception as e:
            log_error_with_context(
                e,
                operation="github_authentication",
                additional_context={"suggested_action": "check_backend_status"},
                include_traceback=True,
            )
            return False
