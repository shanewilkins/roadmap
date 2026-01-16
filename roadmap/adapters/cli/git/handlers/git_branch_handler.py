"""Handler for Git branch operations."""

import structlog
from rich.console import Console

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.core.domain import Issue, Status
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = structlog.get_logger()


class GitBranchHandler:
    """Handles Git branch creation, linking, and validation."""

    def __init__(self, console: Console):
        """Initialize handler with console for output.

        Args:
            console: Rich Console instance
        """
        self.console = console

    def validate_branch_environment(self, core: RoadmapCore) -> bool:
        """Validate roadmap and git environment for branch creation.

        Args:
            core: RoadmapCore instance

        Returns:
            True if environment is valid
        """
        if not core.is_initialized():
            self.console.print(
                "❌ Roadmap not initialized. Run 'roadmap init' first.",
                style="bold red",
            )
            return False

        if not core.git.is_git_repository():
            self.console.print("❌ Not in a Git repository", style="bold red")
            return False

        return True

    def get_and_validate_issue(self, core: RoadmapCore, issue_id: str):
        """Get and validate issue exists.

        Args:
            core: RoadmapCore instance
            issue_id: Issue ID to retrieve

        Returns:
            Issue object or None if not found
        """
        issue = core.issues.get(issue_id)
        if not issue:
            self.console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return None
        return issue

    def create_branch(self, core: RoadmapCore, issue_id: str, checkout: bool = True):
        """Create a Git branch for an issue.

        Args:
            core: RoadmapCore instance
            issue_id: ID of the issue to create branch for
            checkout: Whether to checkout the new branch

        Raises:
            Exception: If branch creation fails
        """
        if not self.validate_branch_environment(core):
            return

        try:
            issue = self.get_and_validate_issue(core, issue_id)
            if not issue:
                return

            branch_name = core.git.suggest_branch_name(issue_id)
            if not branch_name:
                self.console.print(
                    "❌ Could not suggest branch name for issue", style="bold red"
                )
                return

            # Create the branch (use a compatibility wrapper)
            success = self._safe_create_branch(core.git, issue, checkout=checkout)

            if success:
                self._display_branch_success(branch_name, issue, checkout)
                self._update_issue_status_if_needed(core, issue, issue_id)
            else:
                # Try a direct git fallback using subprocess
                import subprocess

                try:
                    subprocess.run(
                        ["git", "checkout", "-b", branch_name],
                        cwd=core.git.repo_path,
                        check=True,
                        capture_output=True,
                    )
                    self._display_branch_success(branch_name, issue, checkout)
                    self._update_issue_status_if_needed(core, issue, issue_id)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    self.console.print("❌ Failed to create branch", style="bold red")

        except Exception as e:
            handle_cli_error(
                error=e,
                operation="create_git_branch",
                entity_type="issue",
                entity_id=issue_id,
                context={"checkout": checkout},
                fatal=True,
            )
            self.console.print(f"❌ Failed to create Git branch: {e}", style="bold red")

    def link_issue_to_branch(self, core: RoadmapCore, issue_id: str):
        """Link an issue to the current Git branch.

        Args:
            core: RoadmapCore instance
            issue_id: ID of the issue to link

        Raises:
            Exception: If linking fails
        """
        if not core.git.is_git_repository():
            self.console.print("❌ Not in a Git repository", style="bold red")
            return

        try:
            issue = core.issues.get(issue_id)
            if not issue:
                self.console.print(f"❌ Issue not found: {issue_id}", style="bold red")
                return

            current_branch = core.git.get_current_branch()
            if not current_branch:
                self.console.print(
                    "❌ Could not determine current branch", style="bold red"
                )
                return

            # Link the issue to the current branch
            success = core.git.link_issue_to_branch(issue_id)

            if success:
                self.console.print(
                    f"🔗 Linked issue to branch: {current_branch}",
                    style="bold green",
                )
                self.console.print(f"📋 Issue: {issue.title}", style="cyan")
                self.console.print(f"🆔 ID: {issue_id}", style="dim")
            else:
                self.console.print(
                    "❌ Failed to link issue to branch", style="bold red"
                )

        except Exception as e:
            handle_cli_error(
                error=e,
                operation="link_issue_to_branch",
                entity_type="issue",
                entity_id=issue_id,
                context={},
                fatal=True,
            )
            self.console.print(
                f"❌ Failed to link issue to Git branch: {e}", style="bold red"
            )

    def _safe_create_branch(self, git, issue, checkout=True) -> bool:
        """Safely create branch with fallback attempts.

        Args:
            git: Git executor
            issue: Issue object
            checkout: Whether to checkout the new branch

        Returns:
            True if branch was created
        """
        try:
            return git.create_branch_for_issue(issue, checkout=checkout)
        except TypeError as e:
            handle_cli_error(
                error=e,
                operation="create_branch_for_issue",
                entity_type="issue",
                entity_id=issue.id,
                context={"checkout": checkout, "error_type": "TypeError"},
                fatal=False,
            )
            try:
                return git.create_branch_for_issue(issue)
            except Exception as e:
                handle_cli_error(
                    error=e,
                    operation="create_branch_for_issue_fallback",
                    entity_type="issue",
                    entity_id=issue.id,
                    context={},
                    fatal=False,
                )
                return False

    def _display_branch_success(self, branch_name: str, issue, checkout: bool) -> None:
        """Display success messages for branch creation.

        Args:
            branch_name: Name of created branch
            issue: Issue object
            checkout: Whether branch was checked out
        """
        self.console.print(f"🌿 Created branch: {branch_name}", style="bold green")
        if checkout:
            self.console.print(f"✅ Checked out branch: {branch_name}", style="green")
        self.console.print(f"🔗 Linked to issue: {issue.title}", style="cyan")

    def _update_issue_status_if_needed(
        self, core: RoadmapCore, issue: Issue, issue_id: str
    ) -> None:
        """Update issue status to in-progress if it's todo.

        Args:
            core: RoadmapCore instance
            issue: Issue object
            issue_id: Issue ID
        """
        if issue.status == Status.TODO:
            core.issues.update(issue_id, status=Status.IN_PROGRESS)
            self.console.print(
                "📊 Updated issue status to: in-progress", style="yellow"
            )
