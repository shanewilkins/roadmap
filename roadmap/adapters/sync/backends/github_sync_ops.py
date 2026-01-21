"""GitHub synchronization operations with parallel execution."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

from roadmap.common.logging import log_error_with_context
from roadmap.core.interfaces import SyncReport

logger = get_logger()


class GitHubSyncOps:
    def __init__(self, backend: Any):
        """Initialize GitHubSyncOps.

        Args:
            backend: GitHub backend instance.
        """
        self.backend = backend

    def push_issues(self, local_issues: list) -> SyncReport:
        report = SyncReport()

        if not local_issues:
            logger.info("push_issues_empty")
            return report

        logger.info("push_issues_starting", issue_count=len(local_issues))

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
                futures = {
                    executor.submit(self.backend.push_issue, issue): issue
                    for issue in local_issues
                }

                for future in as_completed(futures):
                    issue = futures[future]
                    try:
                        if future.result():
                            report.pushed.append(issue.id)
                            status = "✓"
                            logger.debug("push_issue_succeeded", issue_id=issue.id)
                        else:
                            error_msg = "Failed to push issue"
                            report.errors[issue.id] = error_msg
                            status = "✗"
                            logger.warning("push_issue_failed", issue_id=issue.id)
                    except Exception as e:
                        error_msg = str(e)
                        report.errors[issue.id] = error_msg
                        status = "✗"
                        log_error_with_context(
                            e,
                            operation="push_issue_concurrent",
                            entity_type="Issue",
                            entity_id=issue.id,
                            include_traceback=False,
                        )
                    finally:
                        progress.update(
                            task,
                            description=f"[cyan]📤 Pushing {len(report.pushed)}/{len(local_issues)} issues... {status} {issue.id[:8]}",
                        )
                        progress.advance(task)

        logger.info(
            "push_issues_completed",
            total=len(local_issues),
            pushed=len(report.pushed),
            failed=len(report.errors),
        )
        return report

    def pull_issues(self, issue_ids: list[str]) -> SyncReport:
        report = SyncReport()

        if not issue_ids:
            return report

        try:
            logger.info("pull_issues_starting", issue_count=len(issue_ids))

            successful_pulls = []
            failed_pulls = {}

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
                    futures = {
                        executor.submit(self.backend.pull_issue, issue_id): issue_id
                        for issue_id in issue_ids
                    }

                    for future in as_completed(futures):
                        issue_id = futures[future]
                        try:
                            success = future.result()
                            if success:
                                successful_pulls.append(issue_id)
                                status = "✓"
                                logger.debug("pull_issue_succeeded", issue_id=issue_id)
                            else:
                                error_msg = "Pull failed"
                                failed_pulls[issue_id] = error_msg
                                status = "✗"
                                logger.warning("pull_issue_failed", issue_id=issue_id)
                        except Exception as e:
                            error_msg = str(e)
                            failed_pulls[issue_id] = error_msg
                            status = "✗"
                            log_error_with_context(
                                e,
                                operation="pull_issue_concurrent",
                                entity_type="Issue",
                                entity_id=issue_id,
                                include_traceback=False,
                            )
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
                "pull_issues_failed", error=str(e), error_type=type(e).__name__
            )
            report.error = f"Failed to pull issues: {str(e)}"
            return report
