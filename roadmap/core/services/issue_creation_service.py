"""
Service for issue creation operations.

Consolidates business logic for creating issues, including assignee resolution,
Git branch creation, and formatted display of created issues.
"""

import os
import subprocess

import click

from roadmap.common.console import get_console


class IssueCreationService:
    """Service for creating issues with all supporting operations."""

    def __init__(self, core):
        """Initialize service with core instance.

        Args:
            core: RoadmapCore instance
        """
        self.core = core
        self._console = get_console()

    # ─────────────────────────────────────────────────────────────────────────
    # Assignee Resolution
    # ─────────────────────────────────────────────────────────────────────────

    def resolve_and_validate_assignee(
        self, assignee: str | None = None, auto_detect: bool = True
    ) -> str | None:
        """
        Resolve and validate an assignee.

        Auto-detects from Git if not provided. Validates against team members
        and returns canonical name.

        Args:
            assignee: Assignee name to resolve (optional)
            auto_detect: Whether to auto-detect from Git if not provided

        Returns:
            Canonical assignee name or None if not assigned

        Raises:
            click.Abort: If assignee validation fails
        """
        # Auto-detect from Git if not provided
        if not assignee and auto_detect:
            git_user = self.core.git.get_current_user()
            if git_user:
                self._console.print(
                    f"🔍 Auto-detected assignee from Git: {git_user}", style="dim"
                )
                assignee = git_user

        if not assignee:
            return None

        # Validate assignee
        is_valid, result = self.core.team.validate_assignee(assignee)
        if not is_valid:
            self._console.print(f"[ERROR] Invalid assignee: {result}")
            raise click.Abort()

        if result and "Warning:" in result:
            self._console.print(f"⚠️  {result}", style="bold yellow")
            return assignee

        # Get canonical name
        canonical = self.core.team.get_canonical_assignee(assignee)
        if canonical != assignee:
            self._console.print(
                f"🔄 Resolved '{assignee}' to '{canonical}'", style="dim"
            )

        return canonical

    # ─────────────────────────────────────────────────────────────────────────
    # Git Branch Creation
    # ─────────────────────────────────────────────────────────────────────────

    def create_branch_for_issue(
        self,
        issue,
        branch_name: str | None = None,
        checkout: bool = True,
        force: bool = False,
    ) -> tuple[bool, str | None]:
        """
        Create a Git branch for an issue.

        Attempts multiple strategies to create and checkout the branch, with
        fallbacks for various failure scenarios.

        Args:
            issue: Issue object to create branch for
            branch_name: Explicit branch name (optional)
            checkout: Whether to checkout the branch
            force: Whether to force override uncommitted changes

        Returns:
            Tuple of (success: bool, branch_name: Optional[str])
        """
        if not hasattr(self.core, "git") or not self.core.git.is_git_repository():
            self._console.print(
                "⚠️  Not in a Git repository, skipping branch creation", style="yellow"
            )
            return False, None

        # Determine branch name
        resolved_name = branch_name or self.core.git.suggest_branch_name(issue.id)

        # Try primary method
        if self._try_safe_create_branch(issue, checkout, force):
            self._show_branch_success_message(resolved_name, checkout)
            return True, resolved_name

        # Check for uncommitted changes
        if self._has_uncommitted_changes():
            self._console.print(
                "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                style="yellow",
            )
            return False, resolved_name

        # Try fallback strategies
        if self._try_direct_git_command(resolved_name, checkout):
            return True, resolved_name

        if self._try_subprocess_git(resolved_name, checkout):
            return True, resolved_name

        # All strategies failed
        self._console.print(
            "⚠️  Failed to create or checkout branch. See git for details.",
            style="yellow",
        )
        return False, resolved_name

    def _try_safe_create_branch(self, issue, checkout: bool, force: bool) -> bool:
        """Try creating branch using core.git method."""
        try:
            return self.core.git.create_branch_for_issue(
                issue, checkout=checkout, force=force
            )
        except TypeError:
            # Try without force parameter
            try:
                return self.core.git.create_branch_for_issue(issue, checkout=checkout)
            except TypeError:
                # Try with just issue
                try:
                    return self.core.git.create_branch_for_issue(issue)
                except Exception:
                    return False

    def _has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        try:
            status_output = (
                self.core.git._run_git_command(["status", "--porcelain"]) or ""
            )
            return bool(status_output.strip())
        except Exception:
            return False

    def _try_direct_git_command(self, branch_name: str, checkout: bool) -> bool:
        """Try creating branch using direct git command via core.git."""
        try:
            result = self.core.git._run_git_command(["checkout", "-b", branch_name])
            if result is not None:
                self._show_branch_success_message(branch_name, checkout)
                return True

            # Check if branch exists
            exists = self.core.git._run_git_command(
                ["rev-parse", "--verify", branch_name]
            )
            if exists:
                self._show_branch_success_message(branch_name, checkout)
                return True
        except Exception:
            pass
        return False

    def _try_subprocess_git(self, branch_name: str, checkout: bool) -> bool:
        """Try creating branch using subprocess as last resort."""
        try:
            cwd = getattr(self.core, "root_path", None) or os.getcwd()
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
            )
            self._show_branch_success_message(branch_name, checkout)
            return True
        except Exception:
            return False

    def _show_branch_success_message(self, branch_name: str, checkout: bool) -> None:
        """Display success message for branch creation."""
        self._console.print(f"🌿 Created Git branch: {branch_name}", style="green")
        if checkout:
            self._console.print(f"✅ Checked out branch: {branch_name}", style="green")

    # ─────────────────────────────────────────────────────────────────────────
    # Display Formatting
    # ─────────────────────────────────────────────────────────────────────────

    def format_created_issue_display(self, issue, milestone: str | None = None) -> None:
        """
        Display formatted information about a newly created issue.

        Args:
            issue: Created issue object
            milestone: Optional milestone name
        """
        self._console.print(f"✅ Created issue: {issue.title}", style="bold green")
        self._console.print(f"   ID: {issue.id}", style="cyan")
        self._console.print(f"   Type: {issue.issue_type.value.title()}", style="blue")
        self._console.print(f"   Priority: {issue.priority.value}", style="yellow")

        if milestone:
            self._console.print(f"   Milestone: {milestone}", style="blue")

        # Show assignee from issue object (which has the canonical/resolved value)
        if issue.assignee:
            self._console.print(f"   Assignee: {issue.assignee}", style="magenta")

        if issue.estimated_hours:
            self._console.print(
                f"   Estimated: {issue.estimated_time_display}", style="green"
            )

        if hasattr(issue, "depends_on") and issue.depends_on:
            self._console.print(
                f"   Depends on: {', '.join(issue.depends_on)}", style="orange1"
            )

        if hasattr(issue, "blocks") and issue.blocks:
            self._console.print(f"   Blocks: {', '.join(issue.blocks)}", style="red1")

        self._console.print(f"   File: .roadmap/issues/{issue.filename}", style="dim")
