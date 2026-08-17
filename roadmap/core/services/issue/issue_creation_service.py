"""Temporary bridge for issue-triggered Git branch creation.

Issue creation belongs to the application layer. This bridge remains until Git
side effects move behind an application port in Phase 10.
"""

import os
import subprocess

import structlog

from roadmap.common.console import get_console

logger = structlog.get_logger()


class IssueCreationService:
    """Create a Git branch for an already-created issue."""

    def __init__(self, core):
        self.core = core
        self._console = get_console()

    def create_branch_for_issue(
        self,
        issue,
        branch_name: str | None = None,
        checkout: bool = True,
        force: bool = False,
    ) -> tuple[bool, str | None]:
        """Create a branch through the legacy Git adapter and its fallbacks."""
        if not hasattr(self.core, "git") or not self.core.git.is_git_repository():
            self._console.print(
                "⚠️  Not in a Git repository, skipping branch creation", style="yellow"
            )
            return False, None

        resolved_name = branch_name or self.core.git.suggest_branch_name(issue.id)
        if self._try_safe_create_branch(issue, checkout, force):
            self._show_branch_success_message(resolved_name, checkout)
            return True, resolved_name

        if self._has_uncommitted_changes():
            self._console.print(
                "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                style="yellow",
            )
            return False, resolved_name

        if self._try_direct_git_command(resolved_name, checkout):
            return True, resolved_name
        if self._try_subprocess_git(resolved_name, checkout):
            return True, resolved_name

        self._console.print(
            "⚠️  Failed to create or checkout branch. See git for details.",
            style="yellow",
        )
        return False, resolved_name

    def _try_safe_create_branch(self, issue, checkout: bool, force: bool) -> bool:
        try:
            return self.core.git.create_branch_for_issue(
                issue, checkout=checkout, force=force
            )
        except TypeError:
            try:
                return self.core.git.create_branch_for_issue(issue, checkout=checkout)
            except TypeError:
                try:
                    return self.core.git.create_branch_for_issue(issue)
                except Exception as error:
                    logger.debug(
                        "create_branch_fallback_failed",
                        operation="create_branch_for_issue",
                        error=str(error),
                        action="Returning False",
                    )
                    return False

    def _has_uncommitted_changes(self) -> bool:
        try:
            status = self.core.git._run_git_command(["status", "--porcelain"]) or ""
            return bool(status.strip())
        except Exception as error:
            logger.debug(
                "git_status_check_failed",
                operation="check_git_status",
                error=str(error),
                action="Assuming no changes",
            )
            return False

    def _try_direct_git_command(self, branch_name: str, checkout: bool) -> bool:
        try:
            result = self.core.git._run_git_command(["checkout", "-b", branch_name])
            if result is not None:
                self._show_branch_success_message(branch_name, checkout)
                return True
            if self.core.git._run_git_command(["rev-parse", "--verify", branch_name]):
                self._show_branch_success_message(branch_name, checkout)
                return True
        except Exception as error:
            logger.debug(
                "direct_git_command_failed",
                operation="try_direct_git_command",
                branch=branch_name,
                error=str(error),
                action="Falling back to subprocess",
            )
        return False

    def _try_subprocess_git(self, branch_name: str, checkout: bool) -> bool:
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=getattr(self.core, "root_path", None) or os.getcwd(),
                check=True,
                capture_output=True,
                text=True,
            )
            self._show_branch_success_message(branch_name, checkout)
            return True
        except Exception as error:
            logger.debug(
                "branch_creation_failed",
                branch_name=branch_name,
                error=str(error),
                action="create_branch",
            )
            return False

    def _show_branch_success_message(self, branch_name: str, checkout: bool) -> None:
        self._console.print(f"🌿 Created Git branch: {branch_name}", style="green")
        if checkout:
            self._console.print(f"✅ Checked out branch: {branch_name}", style="green")
