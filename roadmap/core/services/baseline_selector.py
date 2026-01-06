"""Interactive baseline selection utility for team onboarding.

Provides guidance and interactive selection for teams creating their
initial baseline during first sync. Ensures explicit, informed choices
about the agreed-upon starting state.
"""

from enum import Enum
from typing import Any

from structlog import get_logger

logger = get_logger()


class BaselineStrategy(str, Enum):
    """Strategy for creating initial baseline."""

    LOCAL = "local"
    """Use local state as baseline - local code is source of truth."""

    REMOTE = "remote"
    """Use remote state as baseline - remote system is source of truth."""

    INTERACTIVE = "interactive"
    """Let user choose per-issue which state to use as baseline."""


class BaselineSelectionResult:
    """Result of baseline selection for one or more issues."""

    def __init__(
        self,
        strategy: BaselineStrategy,
        selected_issues: dict[str, str] | None = None,
    ):
        """Initialize result.

        Args:
            strategy: The strategy chosen (LOCAL, REMOTE, or INTERACTIVE)
            selected_issues: For INTERACTIVE, dict of issue_id -> "local" or "remote"
        """
        self.strategy = strategy
        self.selected_issues = selected_issues or {}

    def get_baseline_for_issue(
        self,
        issue_id: str,
        local_issue: Any,
        remote_issue: Any,
    ) -> Any:
        """Get the issue state to use as baseline.

        Args:
            issue_id: The issue ID
            local_issue: The local issue object
            remote_issue: The remote issue object

        Returns:
            The issue object/dict to use as baseline
        """
        if self.strategy == BaselineStrategy.LOCAL:
            return local_issue
        elif self.strategy == BaselineStrategy.REMOTE:
            return remote_issue
        elif self.strategy == BaselineStrategy.INTERACTIVE:
            choice = self.selected_issues.get(issue_id, "local")
            return local_issue if choice == "local" else remote_issue

        return local_issue  # Default to local


class InteractiveBaselineSelector:
    """Guides teams through baseline selection during first sync."""

    def __init__(self, console_output_fn=None):
        """Initialize selector.

        Args:
            console_output_fn: Function to use for output (for testing)
        """
        self.console_output_fn = console_output_fn or self._default_output
        self.logger = get_logger()

    def _default_output(self, message: str):
        """Default output to console."""
        print(message)

    def prompt_baseline_strategy(self) -> BaselineStrategy:
        """Prompt team to choose baseline strategy.

        Returns:
            Selected BaselineStrategy
        """
        self.logger.info("baseline_strategy_prompt")

        self.console_output_fn("\n" + "=" * 60)
        self.console_output_fn("BASELINE SELECTION - First Sync Configuration")
        self.console_output_fn("=" * 60)
        self.console_output_fn(
            """
This is your first sync. We need to establish the agreed-upon baseline state
that both local and remote systems accept as the starting point.

Choose one of these strategies:

1. LOCAL - Use your local code as the baseline
   Use this if: Local code is your source of truth
   Effect: Remote will pull all local changes
   Risk: May overwrite remote-only changes

2. REMOTE - Use the remote system as the baseline
   Use this if: Remote system is your source of truth
   Effect: Local will pull all remote changes
   Risk: May overwrite local-only changes

3. INTERACTIVE - Choose per-issue which is the baseline
   Use this if: Different issues have different sources of truth
   Effect: You'll be asked for each changed issue
   Risk: Most time-consuming but most flexible
"""
        )

        while True:
            choice = input("\nEnter your choice (1, 2, or 3): ").strip()
            if choice == "1":
                self.console_output_fn("✓ Selected: LOCAL baseline strategy")
                self.logger.info("baseline_strategy_selected", strategy="local")
                return BaselineStrategy.LOCAL
            elif choice == "2":
                self.console_output_fn("✓ Selected: REMOTE baseline strategy")
                self.logger.info("baseline_strategy_selected", strategy="remote")
                return BaselineStrategy.REMOTE
            elif choice == "3":
                self.console_output_fn("✓ Selected: INTERACTIVE baseline strategy")
                self.logger.info("baseline_strategy_selected", strategy="interactive")
                return BaselineStrategy.INTERACTIVE
            else:
                self.console_output_fn("Invalid choice. Please enter 1, 2, or 3.")

    def prompt_interactive_selections(
        self,
        issues_with_changes: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Prompt user to select baseline for each changed issue.

        Args:
            issues_with_changes: List of issues with dicts containing:
                - issue_id: str
                - title: str
                - local_changes: dict or None
                - remote_changes: dict or None

        Returns:
            Dict of issue_id -> "local" or "remote"
        """
        self.logger.info(
            "interactive_baseline_selection_start",
            issue_count=len(issues_with_changes),
        )

        selections = {}

        self.console_output_fn("\n" + "=" * 60)
        self.console_output_fn("INTERACTIVE BASELINE SELECTION")
        self.console_output_fn("=" * 60)
        self.console_output_fn(
            f"\nFor each of {len(issues_with_changes)} changed issues, "
            "choose which is the baseline:\n"
        )

        for idx, issue in enumerate(issues_with_changes, 1):
            issue_id = issue.get("issue_id", "unknown")
            title = issue.get("title", "Untitled")
            local_changes = issue.get("local_changes", {})
            remote_changes = issue.get("remote_changes", {})

            self.console_output_fn(f"\n[{idx}/{len(issues_with_changes)}] {title}")
            self.console_output_fn(f"    ID: {issue_id}")

            if local_changes:
                self.console_output_fn(f"    Local changes: {local_changes}")
            if remote_changes:
                self.console_output_fn(f"    Remote changes: {remote_changes}")

            choice = None
            while choice is None:
                response = (
                    input("\n    Use LOCAL or REMOTE as baseline? (L/R): ")
                    .strip()
                    .upper()
                )
                if response in ("L", "LOCAL"):
                    choice = "local"
                    self.console_output_fn("    → Using LOCAL as baseline")
                elif response in ("R", "REMOTE"):
                    choice = "remote"
                    self.console_output_fn("    → Using REMOTE as baseline")
                else:
                    self.console_output_fn("    Invalid choice. Enter L or R.")

            selections[issue_id] = choice
            self.logger.debug(
                "interactive_baseline_selected",
                issue_id=issue_id,
                choice=choice,
            )

        self.console_output_fn("\n✓ Baseline selection complete\n")
        self.logger.info(
            "interactive_baseline_selection_complete",
            selections=selections,
        )

        return selections

    def select_baseline(
        self,
        issues_with_changes: list[dict[str, Any]] | None = None,
        strategy: BaselineStrategy | None = None,
    ) -> BaselineSelectionResult:
        """Guide complete baseline selection process.

        Args:
            issues_with_changes: Issues with changes (for interactive mode)
            strategy: Override strategy (for testing/automation)

        Returns:
            BaselineSelectionResult with strategy and selections
        """
        self.logger.info("baseline_selection_start")

        # Get strategy if not provided
        if strategy is None:
            strategy = self.prompt_baseline_strategy()

        # Get specific selections if interactive
        selected_issues = {}
        if strategy == BaselineStrategy.INTERACTIVE and issues_with_changes:
            selected_issues = self.prompt_interactive_selections(issues_with_changes)

        result = BaselineSelectionResult(
            strategy=strategy,
            selected_issues=selected_issues,
        )

        self.logger.info("baseline_selection_complete", strategy=strategy.value)
        return result
