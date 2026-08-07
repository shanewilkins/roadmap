"""Dependency analysis helpers for issue pull ordering."""

from __future__ import annotations

from typing import Any

from structlog import get_logger

from roadmap.core.interfaces import SyncReport

logger = get_logger()


class GitHubIssueDependencyService:
    """Builds issue pull plans and milestone dependency sets."""

    def analyze_issue_dependencies(
        self,
        issue_ids: list[str],
        all_remote_issues: dict[str, Any],
        all_remote_milestones: dict[int, Any],
        report: SyncReport,
    ) -> tuple[list[tuple[str, str, Any]], set[int], SyncReport]:
        """Build list of issues to pull and referenced milestone numbers."""
        issues_to_pull: list[tuple[str, str, Any]] = []
        milestones_needed: set[int] = set()

        for issue_id in issue_ids:
            lookup_id = issue_id[8:] if issue_id.startswith("_remote_") else issue_id

            if lookup_id not in all_remote_issues:
                report.errors[issue_id] = "Issue not found on remote"
                continue

            sync_issue = all_remote_issues[lookup_id]
            issues_to_pull.append((issue_id, lookup_id, sync_issue))

            if sync_issue.milestone:
                milestone_num = self.find_milestone_number(
                    sync_issue.milestone,
                    all_remote_milestones,
                )
                if milestone_num is not None:
                    milestones_needed.add(milestone_num)

        logger.info(
            "dependency_analysis_complete",
            issues_requested=len(issue_ids),
            issues_found=len(issues_to_pull),
            milestones_needed=len(milestones_needed),
        )

        return issues_to_pull, milestones_needed, report

    @staticmethod
    def find_milestone_number(
        milestone_name: str, all_remote_milestones: dict[int, Any]
    ) -> int | None:
        """Find milestone number by matching milestone name."""
        for milestone_num, sync_milestone in all_remote_milestones.items():
            if sync_milestone.name == milestone_name:
                return milestone_num
        return None
