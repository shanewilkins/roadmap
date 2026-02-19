"""Duplicate resolution for sync operations.

This module provides automatic and interactive resolution strategies for
duplicate issues detected during sync operations.
"""

from dataclasses import dataclass

from roadmap.common.logging import get_logger
from roadmap.common.result import Ok, Result
from roadmap.core.domain.issue import Issue
from roadmap.core.services.issue.issue_service import IssueService
from roadmap.core.services.sync.duplicate_detector import (
    DuplicateMatch,
    RecommendedAction,
)

logger = get_logger(__name__)


@dataclass
class ResolutionAction:
    """Action taken to resolve a duplicate match.

    Attributes:
        match: The duplicate match that was resolved
        action_type: Type of action ("merge", "delete", "archive", "skip")
        canonical_issue: The resulting canonical issue
        duplicate_issue_id: ID of the duplicate that was handled
        confidence: Confidence level of the resolution
        error: Error message if resolution failed
    """

    match: DuplicateMatch
    action_type: str  # "merge", "delete", "archive", "skip"
    canonical_issue: Issue | None = None
    duplicate_issue_id: str | None = None
    confidence: float = 0.0
    error: str | None = None


class DuplicateResolver:
    """Resolves duplicate issues automatically or interactively.

    Provides automatic resolution for high-confidence matches and
    interactive CLI prompts for manual review cases.
    """

    def __init__(
        self, issue_service: IssueService, auto_resolve_threshold: float = 0.95
    ) -> None:
        """Initialize duplicate resolver.

        Args:
            issue_service: IssueService for persisting resolution
            auto_resolve_threshold: Minimum confidence for automatic resolution (default: 0.95)
        """
        self.issue_service = issue_service
        self.auto_resolve_threshold = auto_resolve_threshold

    def resolve_automatic(
        self, matches: list[DuplicateMatch]
    ) -> Result[list[ResolutionAction], str]:
        """Automatically resolve high-confidence duplicate matches.

        For each match:
        - If confidence == 1.0 (ID collision): delete duplicate (hard delete)
        - If confidence < 1.0 (fuzzy match): archive duplicate with metadata
        - Merge duplicate data into canonical issue
        - Only processes matches >= auto_resolve_threshold with recommended_action == AUTO_MERGE

        Args:
            matches: List of duplicate matches to resolve

        Returns:
            Ok(list of ResolutionAction) on success
            Err(message) if any resolution fails
        """
        actions: list[ResolutionAction] = []

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
                actions.append(
                    ResolutionAction(
                        match=match,
                        action_type="skip",
                        duplicate_issue_id=match.remote_issue.id,
                        confidence=match.confidence,
                    )
                )
                continue

            logger.info(
                "auto_resolving_duplicate",
                local_id=match.local_issue.id,
                remote_id=match.remote_issue.id,
                match_type=match.match_type.value,
                confidence=match.confidence,
            )

            # Note: We just return the action without merging here, because during sync analysis
            # the remote issue may not exist in the local database yet. Merging happens later
            # in _execute_duplicate_resolution() after both issues are available locally.
            # For cross-repo duplicates, the normal sync process will link them.
            actions.append(
                ResolutionAction(
                    match=match,
                    action_type="link",  # Mark for linking local to remote
                    canonical_issue=match.local_issue,
                    duplicate_issue_id=match.remote_issue.id,
                    confidence=match.confidence,
                )
            )
            continue

        return Ok(actions)

    def resolve_interactive(
        self, matches: list[DuplicateMatch]
    ) -> list[ResolutionAction]:
        """Interactively resolve duplicate matches with CLI prompts.

        Presents each match to the user with detailed information and
        options to merge, keep separate, or skip.

        Args:
            matches: List of duplicate matches requiring manual review

        Returns:
            List of ResolutionAction objects for all matches
        """
        actions: list[ResolutionAction] = []

        if not matches:
            return actions

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
                reason="Rich library not available for interactive prompts. Skipping all matches.",
            )
            # Fallback: skip all matches
            for match in matches:
                actions.append(
                    ResolutionAction(
                        match=match,
                        action_type="skip",
                        duplicate_issue_id=match.remote_issue.id,
                        confidence=match.confidence,
                    )
                )
            return actions

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
                # Merge remote into local using issue service
                merge_result = self.issue_service.merge_issues(
                    match.local_issue.id, match.remote_issue.id
                )
                if isinstance(merge_result, Ok):
                    canonical = merge_result.unwrap()
                    logger.info(
                        "user_merged_duplicate",
                        local_id=match.local_issue.id,
                        remote_id=match.remote_issue.id,
                    )
                    actions.append(
                        ResolutionAction(
                            match=match,
                            action_type="merge",
                            canonical_issue=canonical,
                            duplicate_issue_id=match.remote_issue.id,
                            confidence=match.confidence,
                        )
                    )
                else:
                    logger.warning(
                        "user_merge_failed",
                        local_id=match.local_issue.id,
                        remote_id=match.remote_issue.id,
                        error=merge_result.unwrap_err(),
                    )
                    actions.append(
                        ResolutionAction(
                            match=match,
                            action_type="skip",
                            duplicate_issue_id=match.remote_issue.id,
                            confidence=match.confidence,
                            error=f"Merge failed: {merge_result.unwrap_err()}",
                        )
                    )
            elif action == "keep":
                # Keep both issues separate
                logger.info(
                    "user_kept_separate",
                    local_id=match.local_issue.id,
                    remote_id=match.remote_issue.id,
                )
                actions.append(
                    ResolutionAction(
                        match=match,
                        action_type="keep",
                        duplicate_issue_id=match.remote_issue.id,
                        confidence=match.confidence,
                    )
                )
            else:  # skip
                logger.info(
                    "user_skipped_match",
                    local_id=match.local_issue.id,
                    remote_id=match.remote_issue.id,
                )
                actions.append(
                    ResolutionAction(
                        match=match,
                        action_type="skip",
                        duplicate_issue_id=match.remote_issue.id,
                        confidence=match.confidence,
                    )
                )

        return actions

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
