"""Git branch management and issue linking."""

import re
from pathlib import Path

from structlog import get_logger

from roadmap.adapters.git.git import GitBranch
from roadmap.adapters.git.git_command_executor import GitCommandExecutor

logger = get_logger()


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

    def _generate_title_slug(self, title: str) -> str:
        """Generate slug from issue title.

        Args:
            title: Issue title to slugify

        Returns:
            Slug suitable for branch name
        """
        title_slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title.lower())
        title_slug = re.sub(r"\s+", "-", title_slug)
        return title_slug[:40]  # Limit length

    def _determine_prefix(self, issue) -> str:
        """Determine branch prefix based on issue type/priority.

        Args:
            issue: Issue to inspect

        Returns:
            Prefix for branch name
        """
        prefix = "feature"
        if hasattr(issue, "issue_type"):
            if issue.issue_type == "bug":
                prefix = "bugfix"
            elif issue.issue_type == "documentation":
                prefix = "docs"
        elif issue.priority.value == "critical":
            prefix = "hotfix"
        return prefix

    def _get_branch_template(self) -> str | None:
        """Get branch name template from config.

        Returns:
            Template string or None
        """
        try:
            if self.config:
                defaults = getattr(self.config, "defaults", None)
                if defaults and hasattr(defaults, "get"):
                    return defaults.get("branch_name_template")
        except Exception as e:
            logger.debug("get_branch_name_template_failed", error=str(e))
        return None

    def _format_branch_name(
        self, issue_id: int, slug: str, prefix: str, template: str | None
    ) -> str:
        """Format branch name using template or defaults.

        Args:
            issue_id: Issue ID
            slug: Title slug
            prefix: Branch prefix
            template: Template string or None

        Returns:
            Formatted branch name
        """
        if template:
            try:
                return template.format(id=issue_id, slug=slug, prefix=prefix)
            except Exception as e:
                logger.debug(
                    "format_branch_name_template_failed",
                    template=template,
                    error=str(e),
                    severity="operational",
                )

        return f"{prefix}/{issue_id}-{slug}"

    def suggest_branch_name(self, issue) -> str:
        """Suggest a branch name based on issue information."""
        title_slug = self._generate_title_slug(issue.title)
        prefix = self._determine_prefix(issue)
        template = self._get_branch_template()
        return self._format_branch_name(issue.id, title_slug, prefix, template)

    def _check_working_tree_clean(self, force: bool) -> bool:
        """Check if working tree has uncommitted changes.

        Args:
            force: Skip dirty working tree check

        Returns:
            True if working tree is clean or force is True
        """
        if force:
            return True

        status_output = self.executor.run(["status", "--porcelain"]) or ""
        status_lines = [line for line in status_output.splitlines() if line.strip()]
        has_substantive_changes = any(
            not line.startswith("??") for line in status_lines
        )
        return not has_substantive_changes

    def _branch_already_exists(self, branch_name: str) -> bool:
        """Check if branch already exists.

        Args:
            branch_name: Name of branch to check

        Returns:
            True if branch exists
        """
        existing = self.executor.run(["rev-parse", "--verify", branch_name])
        if not existing:
            existing = self.executor.run(
                ["rev-parse", "--verify", f"refs/heads/{branch_name}"]
            )
        return existing is not None

    def _handle_existing_branch(self, branch_name: str, checkout: bool) -> bool:
        """Handle existing branch (checkout or skip).

        Args:
            branch_name: Name of existing branch
            checkout: Whether to checkout the branch

        Returns:
            True if operation succeeded
        """
        if checkout:
            co = self.executor.run(["checkout", branch_name])
            return co is not None
        else:
            return True

    def _get_current_branch(self) -> str | None:
        """Get current branch name.

        Returns:
            Current branch name or None
        """
        return self.executor.run(["rev-parse", "--abbrev-ref", "HEAD"]) or None

    def _create_and_checkout_branch(self, branch_name: str, checkout: bool) -> bool:
        """Create new branch and optionally return to previous branch.

        Args:
            branch_name: Name of new branch
            checkout: Whether to stay on new branch

        Returns:
            True if successful
        """
        current_branch = self._get_current_branch()

        result = self.executor.run(["checkout", "-b", branch_name])
        if result is None:
            return False

        if not checkout:
            if current_branch:
                self.executor.run(["checkout", current_branch])

        return True

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

        if not self._check_working_tree_clean(force):
            return False

        if self._branch_already_exists(branch_name):
            return self._handle_existing_branch(branch_name, checkout)

        return self._create_and_checkout_branch(branch_name, checkout)

    def _check_existing_issue_for_branch(
        self, branch_name: str, roadmap_core
    ) -> str | None:
        """Check if branch already has associated issue.

        Args:
            branch_name: Branch name
            roadmap_core: RoadmapCore instance

        Returns:
            None if no existing issue
        """
        branch = GitBranch(branch_name)
        existing_issue_id = branch.extract_issue_id()
        if existing_issue_id and roadmap_core.issues.get(existing_issue_id):
            return existing_issue_id
        return None

    def _build_auto_created_issue_data(
        self, branch_name: str, roadmap_core
    ) -> dict | None:
        """Build issue data from branch name.

        Args:
            branch_name: Branch name
            roadmap_core: RoadmapCore instance

        Returns:
            Issue data dict or None if can't extract
        """
        branch = GitBranch(branch_name)
        issue_type = branch.suggests_issue_type() or "feature"
        title = self._extract_title_from_branch_name(branch_name)
        if not title:
            return None

        assignee = self._get_current_user(roadmap_core) or "Unknown"
        content = f"Auto-created from branch: `{branch_name}`\n\nThis issue was automatically created when switching to the branch `{branch_name}`."

        issue_data = {
            "title": title,
            "content": content,
            "assignee": assignee,
            "priority": "medium",
            "status": "in_progress",
        }

        if hasattr(roadmap_core.issues, "create_with_type"):
            issue_data["issue_type"] = issue_type

        return issue_data

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

        # Check if issue already exists
        if self._check_existing_issue_for_branch(branch_name, roadmap_core):
            return None

        # Build issue data
        issue_data = self._build_auto_created_issue_data(branch_name, roadmap_core)
        if not issue_data:
            return None

        # Create the issue
        try:
            issue = roadmap_core.issues.create(**issue_data)
            return issue.id
        except Exception as e:
            logger.error("auto_issue_creation_failed", error=str(e))
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
        except Exception as e:
            logger.debug(
                "branch_issue_extraction_failed", branch_name=branch_name, error=str(e)
            )
            return []
