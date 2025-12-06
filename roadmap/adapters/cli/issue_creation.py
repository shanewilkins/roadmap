"""
Issue creation helpers for CLI commands.
Handles assignee validation, Git branch creation, and display formatting.
"""

import os
import subprocess

import click

from roadmap.common.console import get_console

console = get_console()


class AssigneeResolver:
    """Resolves and validates issue assignees."""

    def __init__(self, core):
        self.core = core

    def resolve_assignee(
        self, assignee: str | None, auto_detect: bool = True
    ) -> str | None:
        """
        Resolve assignee with auto-detection and validation.

        Returns:
            Canonical assignee name or None
        """
        # Auto-detect from Git if not provided
        if not assignee and auto_detect:
            git_user = self.core.get_current_user_from_git()
            if git_user:
                console.print(
                    f"🔍 Auto-detected assignee from Git: {git_user}", style="dim"
                )
                assignee = git_user

        if not assignee:
            return None

        # Validate assignee
        is_valid, result = self.core.validate_assignee(assignee)
        if not is_valid:
            console.print(f"❌ Invalid assignee: {result}", style="bold red")
            raise click.Abort()

        if result and "Warning:" in result:
            console.print(f"⚠️  {result}", style="bold yellow")
            return assignee

        # Get canonical name
        canonical = self.core.get_canonical_assignee(assignee)
        if canonical != assignee:
            console.print(f"🔄 Resolved '{assignee}' to '{canonical}'", style="dim")

        return canonical


class GitBranchCreator:
    """Handles Git branch creation for issues with multiple fallback strategies."""

    def __init__(self, core):
        self.core = core

    def create_branch(
        self,
        issue,
        branch_name: str | None = None,
        checkout: bool = True,
        force: bool = False,
    ) -> tuple[bool, str | None]:
        """
        Create a Git branch for an issue.

        Returns:
            Tuple of (success, branch_name)
        """
        if not hasattr(self.core, "git") or not self.core.git.is_git_repository():
            console.print(
                "⚠️  Not in a Git repository, skipping branch creation", style="yellow"
            )
            return False, None

        # Determine branch name
        resolved_name = branch_name or self.core.git.suggest_branch_name(issue)

        # Try primary method
        if self._try_safe_create_branch(issue, checkout, force):
            self._show_success_message(resolved_name, checkout)
            return True, resolved_name

        # Check for uncommitted changes
        if self._has_uncommitted_changes():
            console.print(
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
        console.print(
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
                self._show_success_message(branch_name, checkout)
                return True

            # Check if branch exists
            exists = self.core.git._run_git_command(
                ["rev-parse", "--verify", branch_name]
            )
            if exists:
                self._show_success_message(branch_name, checkout)
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
            self._show_success_message(branch_name, checkout)
            return True
        except Exception:
            return False

    def _show_success_message(self, branch_name: str, checkout: bool) -> None:
        """Display success message for branch creation."""
        console.print(f"🌿 Created Git branch: {branch_name}", style="green")
        if checkout:
            console.print(f"✅ Checked out branch: {branch_name}", style="green")


class IssueDisplayFormatter:
    """Formats issue information for display."""

    @staticmethod
    def display_created_issue(
        issue, milestone: str | None, assignee: str | None
    ) -> None:
        """Display information about a newly created issue."""
        console.print(f"✅ Created issue: {issue.title}", style="bold green")
        console.print(f"   ID: {issue.id}", style="cyan")
        console.print(f"   Type: {issue.issue_type.value.title()}", style="blue")
        console.print(f"   Priority: {issue.priority.value}", style="yellow")

        if milestone:
            console.print(f"   Milestone: {milestone}", style="blue")

        # Show assignee from issue object (which has the canonical/resolved value)
        if issue.assignee:
            console.print(f"   Assignee: {issue.assignee}", style="magenta")

        if issue.estimated_hours:
            console.print(
                f"   Estimated: {issue.estimated_time_display}", style="green"
            )

        if hasattr(issue, "depends_on") and issue.depends_on:
            console.print(
                f"   Depends on: {', '.join(issue.depends_on)}", style="orange1"
            )

        if hasattr(issue, "blocks") and issue.blocks:
            console.print(f"   Blocks: {', '.join(issue.blocks)}", style="red1")

        console.print(f"   File: .roadmap/issues/{issue.filename}", style="dim")
