"""Duplicate resolution for sync operations.

This module provides automatic and interactive resolution strategies for
duplicate issues detected during sync operations.
"""

from dataclasses import dataclass

from roadmap.common.constants import Status
from roadmap.common.logging import get_logger
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.services.sync.duplicate_detector import (
    DuplicateMatch,
    RecommendedAction,
)

logger = get_logger(__name__)


@dataclass
class ResolutionResult:
    """Result of resolving a duplicate match.

    Attributes:
        match: The duplicate match that was resolved
        action_taken: Action that was taken ("merge_remote", "keep_local", "skip", "manual")
        merged_issue: The resulting merged issue if applicable
        skipped: Whether the match was skipped
    """

    match: DuplicateMatch
    action_taken: str
    merged_issue: Issue | None = None
    skipped: bool = False


class DuplicateResolver:
    """Resolves duplicate issues automatically or interactively.

    Provides automatic resolution for high-confidence matches and
    interactive CLI prompts for manual review cases.
    """

    def __init__(self, auto_resolve_threshold: float = 0.95) -> None:
        """Initialize duplicate resolver.

        Args:
            auto_resolve_threshold: Minimum confidence for automatic resolution (default: 0.95)
        """
        self.auto_resolve_threshold = auto_resolve_threshold

    def resolve_automatic(
        self, matches: list[DuplicateMatch]
    ) -> list[ResolutionResult]:
        """Automatically resolve high-confidence duplicate matches.

        Only resolves matches with confidence >= auto_resolve_threshold and
        recommended_action == AUTO_MERGE.

        Args:
            matches: List of duplicate matches to resolve

        Returns:
            List of ResolutionResult objects for resolved and skipped matches
        """
        results: list[ResolutionResult] = []

        for match in matches:
            # Only auto-resolve if confidence is high enough and action is AUTO_MERGE
            if (
                match.confidence < self.auto_resolve_threshold
                or match.recommended_action != RecommendedAction.AUTO_MERGE
            ):
                logger.debug(
                    "skipping_automatic_resolution",
                    local_id=match.local_issue.id,
                    remote_id=match.remote_issue.id,
                    confidence=match.confidence,
                    recommended_action=match.recommended_action.value,
                )
                continue

            logger.info(
                "auto_resolving_duplicate",
                local_id=match.local_issue.id,
                remote_id=match.remote_issue.id,
                match_type=match.match_type.value,
                confidence=match.confidence,
            )

            # Merge remote issue into local issue
            merged_issue = self._merge_issues(match.local_issue, match.remote_issue)

            results.append(
                ResolutionResult(
                    match=match,
                    action_taken="merged",
                    merged_issue=merged_issue,
                    skipped=False,
                )
            )

        return results

    def resolve_interactive(
        self, matches: list[DuplicateMatch]
    ) -> list[ResolutionResult]:
        """Interactively resolve duplicate matches with CLI prompts.

        Presents each match to the user with detailed information and
        options to merge, keep separate, or skip.

        Args:
            matches: List of duplicate matches requiring manual review

        Returns:
            List of ResolutionResult objects for all matches
        """
        results: list[ResolutionResult] = []

        if not matches:
            return results

        logger.info(
            "starting_interactive_resolution",
            match_count=len(matches),
        )

        # Import Rich here to avoid dependency issues in non-interactive contexts
        try:
            from rich.console import Console
            from rich.prompt import Prompt

            console = Console()
        except ImportError:
            logger.warning(
                "rich_not_available",
                message="Rich library not available for interactive prompts. Skipping all matches.",
            )
            # Fallback: skip all matches
            for match in matches:
                results.append(
                    ResolutionResult(
                        match=match,
                        action_taken="skip",
                        merged_issue=None,
                        skipped=True,
                    )
                )
            return results

        for i, match in enumerate(matches, 1):
            console.print(
                f"\n[bold cyan]Duplicate Match {i}/{len(matches)}[/bold cyan]"
            )
            console.print(self._format_match_details(match))

            # Prompt user for action
            action = Prompt.ask(
                "\nWhat would you like to do?",
                choices=["merge", "keep", "skip"],
                default="skip",
            )

            if action == "merge":
                # Merge remote into local
                merged_issue = self._merge_issues(match.local_issue, match.remote_issue)
                logger.info(
                    "user_merged_duplicate",
                    local_id=match.local_issue.id,
                    remote_id=match.remote_issue.id,
                )
                results.append(
                    ResolutionResult(
                        match=match,
                        action_taken="merge_remote",
                        merged_issue=merged_issue,
                        skipped=False,
                    )
                )
            elif action == "keep":
                # Keep both issues separate
                logger.info(
                    "user_kept_separate",
                    local_id=match.local_issue.id,
                    remote_id=match.remote_issue.id,
                )
                results.append(
                    ResolutionResult(
                        match=match,
                        action_taken="keep_local",
                        merged_issue=None,
                        skipped=False,
                    )
                )
            else:  # skip
                logger.info(
                    "user_skipped_match",
                    local_id=match.local_issue.id,
                    remote_id=match.remote_issue.id,
                )
                results.append(
                    ResolutionResult(
                        match=match,
                        action_taken="skip",
                        merged_issue=None,
                        skipped=True,
                    )
                )

        return results

    def _merge_issues(self, local: Issue, remote: SyncIssue) -> Issue:
        """Merge remote issue data into local issue.

        Creates a new Issue with merged data, preferring remote data
        for fields that are more up-to-date.

        Args:
            local: Local Issue object
            remote: Remote SyncIssue object

        Returns:
            Merged Issue object with combined data
        """
        # Create merged issue, preferring remote for updated fields
        # but keeping local metadata (id, created, etc.)
        merged = Issue(
            id=local.id,
            title=remote.title if remote.title else local.title,
            headline=remote.headline if remote.headline else local.headline,
            content=local.content,  # Keep local content by default
            status=Status(remote.status) if remote.status else local.status,
            priority=local.priority,  # Keep local priority
            issue_type=local.issue_type,
            labels=list(set(local.labels + (remote.labels or []))),  # Merge labels
            assignee=remote.assignee if remote.assignee else local.assignee,
            milestone=remote.milestone if remote.milestone else local.milestone,
            created=local.created,
            updated=remote.updated_at if remote.updated_at else local.updated,
            remote_ids={**local.remote_ids, remote.backend_name: remote.backend_id}
            if remote.backend_id
            else local.remote_ids,
        )

        logger.debug(
            "merged_issue_created",
            local_id=local.id,
            remote_id=remote.id,
            merged_title=merged.title,
        )

        return merged

    def _format_match_details(self, match: DuplicateMatch):
        """Format match details as a Rich panel for display.

        Args:
            match: Duplicate match to format

        Returns:
            Rich Panel with formatted match details, or None if Rich unavailable
        """
        try:
            from rich.panel import Panel
            from rich.table import Table
        except ImportError:
            logger.debug("rich_not_available_for_formatting")
            return None

        # Create comparison table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field", style="cyan")
        table.add_column("Local Issue", style="green")
        table.add_column("Remote Issue", style="yellow")

        # Add rows
        table.add_row("ID", match.local_issue.id, match.remote_issue.id)
        table.add_row("Title", match.local_issue.title, match.remote_issue.title)
        table.add_row(
            "Status",
            match.local_issue.status.value,
            match.remote_issue.status or "unknown",
        )
        table.add_row(
            "Assignee",
            match.local_issue.assignee or "unassigned",
            match.remote_issue.assignee or "unassigned",
        )

        # Add similarity details
        details_text = f"\n[bold]Match Type:[/bold] {match.match_type.value}\n"
        details_text += f"[bold]Confidence:[/bold] {match.confidence:.1%}\n"
        details_text += (
            f"[bold]Recommendation:[/bold] {match.recommended_action.value}\n"
        )

        if match.similarity_details:
            details_text += "\n[bold]Similarity Details:[/bold]\n"
            for key, value in match.similarity_details.items():
                if isinstance(value, float):
                    details_text += f"  • {key}: {value:.1%}\n"
                else:
                    details_text += f"  • {key}: {value}\n"

        content = f"{details_text}\n{table}"

        return Panel(
            content,
            title=f"Potential Duplicate: {match.match_type.value}",
            border_style="yellow",
        )
