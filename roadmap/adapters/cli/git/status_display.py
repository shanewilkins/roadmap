"""Display helper for git status command."""

from typing import Any

from rich.console import Console


class GitStatusDisplay:
    """Handles display of git status information."""

    def __init__(self, console: Console):
        """Initialize with a console for output.

        Args:
            console: Rich console instance for formatted output
        """
        self.console = console

    def show_not_git_repo(self) -> None:
        """Display message when not in a git repository."""
        self.console.print("📁 Not in a Git repository", style="yellow")

    def show_header(self) -> None:
        """Display the status header."""
        self.console.print("🔍 Git Repository Status", style="bold blue")
        self.console.print()

    def show_repository_info(self, git_context: dict[str, Any]) -> None:
        """Display repository origin and GitHub information.

        Args:
            git_context: Dictionary containing git context information
        """
        if git_context.get("origin_url"):
            self.console.print(f"📍 Origin: {git_context['origin_url']}", style="cyan")

        if git_context.get("github_owner") and git_context.get("github_repo"):
            self.console.print(
                f"🐙 GitHub: {git_context['github_owner']}/{git_context['github_repo']}",
                style="cyan",
            )

    def show_current_branch(self, git_context: dict[str, Any]) -> None:
        """Display current branch and linked issue information.

        Args:
            git_context: Dictionary containing git context information
        """
        if not git_context.get("current_branch"):
            return

        self.console.print(
            f"🌿 Current branch: {git_context['current_branch']}", style="green"
        )

        linked_issue = git_context.get("linked_issue")
        if linked_issue:
            self._show_linked_issue_details(linked_issue)
        else:
            self.console.print("   💡 No linked issue found", style="dim")

    def _show_linked_issue_details(self, linked_issue: dict[str, Any]) -> None:
        """Display details of the linked issue.

        Args:
            linked_issue: Dictionary containing linked issue information
        """
        self.console.print("🔗 Linked issue:", style="bold")
        self.console.print(f"   📋 {linked_issue['title']}", style="cyan")
        self.console.print(f"   🆔 {linked_issue['id']}", style="dim")
        self.console.print(f"   📊 Status: {linked_issue['status']}", style="yellow")

        priority_style = "red" if linked_issue["priority"] == "critical" else "yellow"
        self.console.print(
            f"   ⚡ Priority: {linked_issue['priority']}", style=priority_style
        )

    def show_branch_issue_links(
        self, branch_issues: dict[str, list[str]], current_branch: str, core: Any
    ) -> None:
        """Display all branch-issue mappings.

        Args:
            branch_issues: Dictionary mapping branches to issue IDs
            current_branch: Name of the current branch
            core: RoadmapCore instance for fetching issue details
        """
        if not branch_issues:
            return

        self.console.print("\n🌿 Branch-Issue Links:", style="bold")

        for branch, issue_ids in branch_issues.items():
            for issue_id in issue_ids:
                issue = core.get_issue(issue_id)
                if issue:
                    self._show_branch_issue_link(branch, issue, current_branch)

    def _show_branch_issue_link(
        self, branch: str, issue: Any, current_branch: str
    ) -> None:
        """Display a single branch-issue link.

        Args:
            branch: Branch name
            issue: Issue object
            current_branch: Name of the current branch
        """
        marker = "👉" if branch == current_branch else "  "
        title = issue.title[:50]
        if len(issue.title) > 50:
            title += "..."

        self.console.print(f"{marker} {branch} → {title}", style="cyan")

    def show_recent_commits(self, core: Any) -> None:
        """Display recent commits with roadmap references.

        Args:
            core: RoadmapCore instance for fetching commit information
        """
        if not core.git.is_git_repository():
            return

        recent_commits = core.git.get_recent_commits(count=5)
        roadmap_commits = [c for c in recent_commits if c.extract_roadmap_references()]

        if not roadmap_commits:
            return

        self.console.print("\n📝 Recent Roadmap Commits:", style="bold")

        for commit in roadmap_commits[:3]:
            self._show_commit_details(commit)

    def _show_commit_details(self, commit: Any) -> None:
        """Display details of a single commit.

        Args:
            commit: Commit object with message and references
        """
        message = commit.message[:60]
        if len(commit.message) > 60:
            message += "..."

        self.console.print(f"   {commit.short_hash} {message}", style="dim")

        refs = commit.extract_roadmap_references()
        if refs:
            self.console.print(f"     🔗 References: {', '.join(refs)}", style="cyan")

    def show_error(self, error: Exception) -> None:
        """Display an error message.

        Args:
            error: Exception that occurred
        """
        self.console.print(f"❌ Failed to get Git status: {error}", style="bold red")
