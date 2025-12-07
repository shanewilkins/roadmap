"""Git branch management and issue linking."""

import re
from pathlib import Path

from roadmap.adapters.git.git import GitBranch
from roadmap.adapters.git.git_command_executor import GitCommandExecutor


class GitBranchManager:
    """Manages Git branches and links them to roadmap issues."""

    def __init__(self, repo_path: Path | None = None, config: object | None = None):
        """Initialize branch manager."""
        self.executor = GitCommandExecutor(repo_path)
        self.repo_path = repo_path or Path.cwd()
        self.config = config

    def get_current_branch(self) -> GitBranch | None:
        """Get information about the current branch."""
        branch_name = self.executor.run(["rev-parse", "--abbrev-ref", "HEAD"])
        if not branch_name or branch_name == "HEAD":
            return None

        # Get remote tracking branch
        remote = self.executor.run(
            ["rev-parse", "--abbrev-ref", f"{branch_name}@{{upstream}}"]
        )

        # Get last commit
        last_commit = self.executor.run(["rev-parse", "HEAD"])

        return GitBranch(
            name=branch_name, current=True, remote=remote, last_commit=last_commit
        )

    def get_all_branches(self) -> list[GitBranch]:
        """Get all local branches."""
        output = self.executor.run(["branch", "--format=%(refname:short)|%(HEAD)"])
        if not output:
            return []

        branches = []
        for line in output.split("\n"):
            if "|" not in line:
                continue

            name, head_marker = line.split("|", 1)
            is_current = head_marker.strip() == "*"

            branches.append(GitBranch(name=name.strip(), current=is_current))

        return branches

    def suggest_branch_name(self, issue) -> str:
        """Suggest a branch name based on issue information."""
        # Clean title for branch name
        title_slug = re.sub(r"[^a-zA-Z0-9\s-]", "", issue.title.lower())
        title_slug = re.sub(r"\s+", "-", title_slug)
        title_slug = title_slug[:40]  # Limit length

        # Determine prefix based on issue type or priority
        prefix = "feature"
        if hasattr(issue, "issue_type"):
            if issue.issue_type == "bug":
                prefix = "bugfix"
            elif issue.issue_type == "documentation":
                prefix = "docs"
        elif issue.priority.value == "critical":
            prefix = "hotfix"

        # Use branch name template from config if provided
        template = None
        try:
            if self.config:
                defaults = getattr(self.config, "defaults", None)
                if defaults and hasattr(defaults, "get"):
                    template = defaults.get("branch_name_template")
        except Exception:
            template = None

        if template:
            # Allow template placeholders: {id}, {slug}, {prefix}
            try:
                return template.format(id=issue.id, slug=title_slug, prefix=prefix)
            except Exception:
                # Fall back to default if template formatting fails
                pass

        return f"{prefix}/{issue.id}-{title_slug}"

    def create_branch_for_issue(
        self, issue, checkout: bool = True, force: bool = False
    ) -> bool:
        """Create a new branch for an issue.

        Args:
            issue: Issue object with id and title
            checkout: Whether to checkout the new branch
            force: Skip dirty working tree check

        Returns:
            True if successful, False otherwise
        """
        if not self.executor.is_git_repository():
            return False

        branch_name = self.suggest_branch_name(issue)

        # Check for uncommitted changes
        status_output = self.executor.run(["status", "--porcelain"]) or ""
        # Consider only substantive changes as dirty: ignore purely untracked files (??)
        status_lines = [line for line in status_output.splitlines() if line.strip()]
        has_substantive_changes = any(
            not line.startswith("??") for line in status_lines
        )
        if has_substantive_changes and not force:
            # Working tree has tracked modifications; do not create branch by default
            return False

        # Check if branch already exists
        existing = self.executor.run(["rev-parse", "--verify", branch_name])
        if not existing:
            existing = self.executor.run(
                ["rev-parse", "--verify", f"refs/heads/{branch_name}"]
            )
        # If branch exists, optionally checkout it
        if existing:
            if checkout:
                co = self.executor.run(["checkout", branch_name])
                return co is not None
            else:
                # Branch exists but we are not checking out; success
                return True

        # Remember current branch
        current_branch = (
            self.executor.run(["rev-parse", "--abbrev-ref", "HEAD"]) or None
        )

        # Create the branch
        result = self.executor.run(["checkout", "-b", branch_name])
        if result is None:
            return False

        if not checkout:
            # Switch back to previous branch if we created branch but shouldn't stay on it
            if current_branch:
                self.executor.run(["checkout", current_branch])

        return True

    def auto_create_issue_from_branch(
        self, roadmap_core, branch_name: str | None = None
    ) -> str | None:
        """Automatically create an issue from a branch name if one doesn't exist.

        Args:
            roadmap_core: RoadmapCore instance for issue operations
            branch_name: Branch name to analyze. If None, uses current branch.

        Returns:
            Issue ID if created, None if not created or already exists
        """
        if branch_name is None:
            current_branch = self.get_current_branch()
            if not current_branch:
                return None
            branch_name = current_branch.name

        # Don't create issues for main branches
        if branch_name in ["main", "master", "develop", "dev"]:
            return None

        branch = GitBranch(branch_name)

        # Check if branch already has an associated issue
        existing_issue_id = branch.extract_issue_id()
        if existing_issue_id:
            # Check if the issue actually exists
            if roadmap_core.issues.get(existing_issue_id):
                return None  # Issue already exists

        # Generate issue details from branch name
        issue_type = branch.suggests_issue_type() or "feature"

        # Extract title from branch name
        title = self._extract_title_from_branch_name(branch_name)
        if not title:
            return None

        # Create the issue
        try:
            assignee = self._get_current_user(roadmap_core) or "Unknown"

            content = f"Auto-created from branch: `{branch_name}`\n\nThis issue was automatically created when switching to the branch `{branch_name}`."

            issue_data = {
                "title": title,
                "content": content,
                "assignee": assignee,
                "priority": "medium",  # Default priority
                "status": "in_progress",  # Since they're working on it
            }

            # Add issue type if the models support it
            if hasattr(roadmap_core.issues, "create_with_type"):
                issue_data["issue_type"] = issue_type

            issue = roadmap_core.issues.create(**issue_data)
            return issue.id

        except Exception:
            return None

    def _extract_title_from_branch_name(self, branch_name: str) -> str | None:
        """Extract a readable title from a branch name."""
        # Remove common prefixes
        name = branch_name
        prefixes = [
            "feature/",
            "bugfix/",
            "hotfix/",
            "docs/",
            "test/",
            "feat/",
            "bug/",
            "fix/",
        ]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix) :]
                break

        # Remove issue ID if present
        name = re.sub(r"^[a-f0-9]{8}-", "", name)
        name = re.sub(r"^issue-[a-f0-9]{8}-", "", name)

        # Replace hyphens/underscores with spaces and title case
        name = re.sub(r"[-_]", " ", name)
        name = name.strip()

        if not name:
            return None

        # Title case
        words = name.split()
        title_words = []
        for word in words:
            if len(word) > 3:  # Title case for longer words
                title_words.append(word.capitalize())
            else:  # Keep short words lowercase unless first word
                title_words.append(word.lower() if title_words else word.capitalize())

        return " ".join(title_words)

    def _get_current_user(self, roadmap_core) -> str | None:
        """Get current Git user name."""
        return self.executor.run(["config", "user.name"])

    def get_branch_linked_issues(self, branch_name: str) -> list[str]:
        """Get issue IDs linked to a specific branch."""
        try:
            # Create a GitBranch object and extract issue ID
            branch = GitBranch(branch_name)
            issue_id = branch.extract_issue_id()

            if issue_id:
                return [issue_id]
            else:
                return []
        except Exception:
            return []
