"""GitHub issue deletion service using GraphQL batch mutations."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from structlog import get_logger

logger = get_logger()


class GitHubIssueDeleteService:
    """Handles issue deletion flow and GraphQL request orchestration."""

    def __init__(self, config: dict[str, Any]):
        """Initialize the delete service with backend configuration."""
        self.config = config

    def delete_issues(self, issue_numbers: list[int]) -> int:
        """Delete GitHub issues by number and return the delete count."""
        if not issue_numbers:
            return 0

        config = self.get_delete_issue_config()
        if config is None:
            return 0
        token, owner, repo = config

        start_time = time.time()
        logger.info(
            "github_delete_issues_starting",
            requested_count=len(issue_numbers),
        )

        deleted_count = 0
        skipped_pr_numbers: list[int] = []
        lookup_batch_size = 20
        delete_batch_size = 5
        inter_batch_delay_seconds = 0.2
        rate_limit_delay_seconds = 1.0

        for i in range(0, len(issue_numbers), lookup_batch_size):
            batch = issue_numbers[i : i + lookup_batch_size]
            batch_deleted, batch_skipped_prs = self.process_issue_lookup_batch(
                batch=batch,
                owner=owner,
                repo=repo,
                token=token,
                delete_batch_size=delete_batch_size,
                inter_batch_delay_seconds=inter_batch_delay_seconds,
                rate_limit_delay_seconds=rate_limit_delay_seconds,
            )
            deleted_count += batch_deleted
            skipped_pr_numbers.extend(batch_skipped_prs)

        duration = time.time() - start_time
        failed_count = max(
            0, len(issue_numbers) - deleted_count - len(skipped_pr_numbers)
        )
        if skipped_pr_numbers:
            logger.info(
                "github_delete_issues_prs_skipped",
                skipped_count=len(skipped_pr_numbers),
                skipped_numbers=skipped_pr_numbers[:20],
            )

        logger.info(
            "github_delete_issues_completed",
            requested_count=len(issue_numbers),
            deleted_count=deleted_count,
            failed_count=failed_count,
            skipped_pr_count=len(skipped_pr_numbers),
            duration_seconds=round(duration, 3),
        )

        return deleted_count

    def get_delete_issue_config(self) -> tuple[str, str, str] | None:
        """Return token, owner, and repo when delete prerequisites are present."""
        token = self.config.get("token")
        owner = self.config.get("owner")
        repo = self.config.get("repo")
        if token and owner and repo:
            return str(token), str(owner), str(repo)

        logger.warning(
            "github_delete_issues_missing_config",
            has_token=bool(token),
            has_owner=bool(owner),
            has_repo=bool(repo),
        )
        return None

    def process_issue_lookup_batch(
        self,
        *,
        batch: list[int],
        owner: str,
        repo: str,
        token: str,
        delete_batch_size: int,
        inter_batch_delay_seconds: float,
        rate_limit_delay_seconds: float,
    ) -> tuple[int, list[int]]:
        """Resolve node IDs for a batch and perform batched deletions."""
        node_ids, skipped_prs = self.resolve_issue_node_ids(batch, owner, repo, token)
        if not node_ids:
            logger.warning(
                "github_delete_issues_batch_skipped",
                batch_size=len(batch),
                reason="node_ids_empty",
            )
            return 0, skipped_prs

        deleted_count = self.delete_issue_node_chunks(
            node_ids=node_ids,
            token=token,
            delete_batch_size=delete_batch_size,
            inter_batch_delay_seconds=inter_batch_delay_seconds,
            rate_limit_delay_seconds=rate_limit_delay_seconds,
        )
        return deleted_count, skipped_prs

    def delete_issue_node_chunks(
        self,
        *,
        node_ids: dict[int, str],
        token: str,
        delete_batch_size: int,
        inter_batch_delay_seconds: float,
        rate_limit_delay_seconds: float,
    ) -> int:
        """Delete node IDs in chunks and retry rate-limited failures once."""
        deleted_count = 0
        node_items = list(node_ids.items())

        for j in range(0, len(node_items), delete_batch_size):
            delete_chunk = dict(node_items[j : j + delete_batch_size])
            batch_deleted, rate_limited, failed_numbers = self.delete_issues_batch(
                delete_chunk,
                token,
            )
            deleted_count += batch_deleted
            logger.info(
                "github_delete_issues_batch_complete",
                batch_size=len(delete_chunk),
                deleted_count=batch_deleted,
            )

            deleted_count += self.retry_failed_rate_limited_deletes(
                failed_numbers=failed_numbers,
                rate_limited=rate_limited,
                node_ids=node_ids,
                token=token,
                rate_limit_delay_seconds=rate_limit_delay_seconds,
            )

            time.sleep(inter_batch_delay_seconds)
            if rate_limited:
                logger.warning(
                    "github_delete_issues_rate_limited",
                    delay_seconds=rate_limit_delay_seconds,
                )
                time.sleep(rate_limit_delay_seconds)

        return deleted_count

    def retry_failed_rate_limited_deletes(
        self,
        *,
        failed_numbers: list[int],
        rate_limited: bool,
        node_ids: dict[int, str],
        token: str,
        rate_limit_delay_seconds: float,
    ) -> int:
        """Retry failed deletes when the preceding batch was rate-limited."""
        if not (failed_numbers and rate_limited):
            return 0

        logger.warning(
            "github_delete_issues_retrying_failed",
            failed_count=len(failed_numbers),
            delay_seconds=rate_limit_delay_seconds,
        )
        time.sleep(rate_limit_delay_seconds)
        retry_items = {
            number: node_ids[number] for number in failed_numbers if number in node_ids
        }
        if not retry_items:
            return 0

        retry_deleted, _, _ = self.delete_issues_batch(retry_items, token)
        return retry_deleted

    def resolve_issue_node_ids(
        self,
        issue_numbers: list[int],
        owner: str,
        repo: str,
        token: str,
    ) -> tuple[dict[int, str], list[int]]:
        """Resolve GraphQL node IDs for issues and collect skipped pull requests."""
        query_parts = []
        for idx, number in enumerate(issue_numbers):
            query_parts.append(
                f'''
                issue{idx}: repository(owner: "{owner}", name: "{repo}") {{
                  issueOrPullRequest(number: {number}) {{
                    __typename
                    ... on Issue {{ id number }}
                    ... on PullRequest {{ id number }}
                  }}
                }}
                '''
            )

        query = "query {" + "\n".join(query_parts) + "\n}"
        response = self.post_graphql_with_backoff(
            query,
            token,
            operation="resolve_issue_node_ids",
        )
        if response is None:
            return {}, []

        data = response.get("data") or {}
        node_ids: dict[int, str] = {}
        skipped_pr_numbers: list[int] = []
        for idx, number in enumerate(issue_numbers):
            key = f"issue{idx}"
            issue_data = data.get(key, {}).get("issueOrPullRequest")
            if issue_data and issue_data.get("__typename") == "Issue":
                if issue_data.get("id"):
                    node_ids[number] = issue_data["id"]
                else:
                    logger.warning("github_issue_node_id_missing", issue_number=number)
            elif issue_data and issue_data.get("__typename") == "PullRequest":
                logger.warning(
                    "github_issue_node_id_skipped_pull_request",
                    issue_number=number,
                )
                skipped_pr_numbers.append(number)
            else:
                logger.warning("github_issue_node_id_missing", issue_number=number)

        logger.info(
            "github_issue_node_ids_resolved",
            requested_count=len(issue_numbers),
            resolved_count=len(node_ids),
        )

        return node_ids, skipped_pr_numbers

    def delete_issues_batch(
        self, node_ids: dict[int, str], token: str
    ) -> tuple[int, bool, list[int]]:
        """Delete a single GraphQL batch and return deleted count and failures."""
        mutation_parts = []
        for idx, (_number, node_id) in enumerate(node_ids.items()):
            mutation_parts.append(
                f'''
                delete{idx}: deleteIssue(input: {{issueId: "{node_id}"}}) {{
                  clientMutationId
                }}
                '''
            )

        mutation = "mutation {" + "\n".join(mutation_parts) + "\n}"
        response = self.post_graphql_with_backoff(
            mutation,
            token,
            operation="delete_issues_batch",
        )
        if response is None:
            return 0, False, list(node_ids.keys())

        error_types = self.extract_graphql_error_types(response)
        error_details = self.extract_graphql_error_details(response)
        rate_limited = "RESOURCE_LIMITS_EXCEEDED" in error_types

        data = response.get("data") or {}
        deleted = 0
        failed_numbers: list[int] = []
        for idx, number in enumerate(node_ids.keys()):
            key = f"delete{idx}"
            if data.get(key) is not None:
                deleted += 1
            else:
                logger.warning("github_issue_delete_failed", issue_number=number)
                failed_numbers.append(number)

        logger.info(
            "github_delete_batch_summary",
            attempted_count=len(node_ids),
            deleted_count=deleted,
        )

        if error_details:
            logger.warning(
                "github_delete_batch_errors",
                error_types=sorted(error_types),
                error_count=len(error_details),
                error_samples=error_details[:5],
                failed_numbers=failed_numbers[:10],
            )

        return deleted, rate_limited, failed_numbers

    @staticmethod
    def extract_graphql_error_types(payload: dict[str, Any]) -> set[str]:
        """Extract distinct GraphQL error type codes from a response payload."""
        errors = payload.get("errors") or []
        return {
            error_type
            for error in errors
            if isinstance(error, dict)
            and isinstance((error_type := error.get("type")), str)
        }

    @staticmethod
    def extract_graphql_error_details(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract lightweight GraphQL error detail entries from a payload."""
        errors = payload.get("errors") or []
        details: list[dict[str, Any]] = []
        for error in errors:
            if not isinstance(error, dict):
                continue
            details.append(
                {
                    "type": error.get("type"),
                    "path": error.get("path"),
                    "message": error.get("message"),
                }
            )
        return details

    def post_graphql_with_backoff(
        self,
        query: str,
        token: str,
        operation: str,
        max_attempts: int = 3,
        delay: float = 2.0,
        backoff: float = 2.0,
        post_graphql_fn=None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> dict[str, Any] | None:
        """Post GraphQL with retry and exponential backoff for transient failures."""
        attempt = 0
        current_delay = delay
        payload: dict[str, Any] | None = None
        sleep = sleep_fn or time.sleep

        while attempt < max_attempts:
            attempt += 1
            if post_graphql_fn is None:
                payload = self.post_graphql(query, token)
            else:
                payload = post_graphql_fn(query, token)
            if payload is None:
                if attempt < max_attempts:
                    logger.warning(
                        "github_graphql_retry_request_failed",
                        operation=operation,
                        attempt=attempt,
                        delay_seconds=current_delay,
                    )
                    sleep(current_delay)
                    current_delay *= backoff
                    continue
                return None

            error_types = self.extract_graphql_error_types(payload)
            if "RESOURCE_LIMITS_EXCEEDED" in error_types and attempt < max_attempts:
                logger.warning(
                    "github_graphql_rate_limited",
                    operation=operation,
                    attempt=attempt,
                    delay_seconds=current_delay,
                )
                sleep(current_delay)
                current_delay *= backoff
                continue

            return payload

        return payload

    @staticmethod
    def post_graphql(query: str, token: str) -> dict[str, Any] | None:
        """Execute a single GraphQL HTTP request and return decoded JSON payload."""
        import requests

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v4+json",
            "User-Agent": "roadmap-cli/1.0",
        }
        try:
            response = requests.post(
                "https://api.github.com/graphql",
                json={"query": query},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                logger.warning(
                    "github_graphql_errors",
                    errors=payload.get("errors"),
                )
            return payload
        except requests.RequestException as e:
            logger.warning(
                "github_graphql_request_failed",
                error=str(e),
                severity="operational",
            )
            return None
