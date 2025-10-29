"""Git integration module for enhanced Git workflow support."""

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import Issue


@dataclass
class GitCommit:
    """Represents a Git commit with roadmap-relevant information."""

    hash: str
    author: str
    date: datetime
    message: str
    files_changed: List[str]
    insertions: int = 0
    deletions: int = 0

    @property
    def short_hash(self) -> str:
        """Get short commit hash."""
        return self.hash[:8]

    def extract_roadmap_references(self) -> List[str]:
        """Extract roadmap issue references from commit message."""
        # Enhanced patterns to support multiple formats:
        # 1. [roadmap:issue-id] or [closes roadmap:issue-id] (existing)
        # 2. fixes #issue-id, closes #issue-id (GitHub/GitLab style)
        # 3. resolves #issue-id, resolve #issue-id
        # 4. addresses #issue-id, refs #issue-id
        # Issue IDs can be hex or alphanumeric
        patterns = [
            # Original roadmap: patterns
            r"\[roadmap:([a-zA-Z0-9]{8,})\]",
            r"\[closes roadmap:([a-zA-Z0-9]{8,})\]",
            r"\[fixes roadmap:([a-zA-Z0-9]{8,})\]",
            r"roadmap:([a-zA-Z0-9]{8,})",
            # GitHub/GitLab style patterns
            r"\b(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#([a-zA-Z0-9]{8,})\b",
            r"\b(?:addresses?|refs?)\s+#([a-zA-Z0-9]{8,})\b",
            # Simple # references
            r"#([a-f0-9]{8})\b",  # Hex issue IDs only for this pattern to avoid false positives
        ]

        references = []
        for pattern in patterns:
            matches = re.findall(pattern, self.message, re.IGNORECASE)
            references.extend(matches)

        return list(set(references))  # Remove duplicates

    def extract_progress_info(self) -> Optional[float]:
        """Extract progress percentage from commit message."""
        # Pattern: [progress:25%] or [progress:25]
        patterns = [
            r"\[progress:(\d+)%?\]",
            r"progress:(\d+)%?",
        ]

        for pattern in patterns:
            match = re.search(pattern, self.message, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None


@dataclass
class GitBranch:
    """Represents a Git branch with roadmap integration info."""

    name: str
    current: bool = False
    remote: Optional[str] = None
    last_commit: Optional[str] = None

    def extract_issue_id(self) -> Optional[str]:
        """Extract issue ID from branch name patterns."""
        # Common patterns:
        # feature/issue-abc12345-description
        # bugfix/abc12345-fix-login
        # abc12345-new-feature
        patterns = [
            r"(?:feature|bugfix|hotfix)/(?:issue-)?([a-f0-9]{8})",
            r"^([a-f0-9]{8})-",
            r"/([a-f0-9]{8})-",
        ]

        for pattern in patterns:
            match = re.search(pattern, self.name, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def suggests_issue_type(self) -> Optional[str]:
        """Suggest issue type based on branch name."""
        if self.name.startswith(("feature/", "feat/")):
            return "feature"
        elif self.name.startswith(("bugfix/", "bug/", "fix/")):
            return "bug"
        elif self.name.startswith(("hotfix/", "urgent/")):
            return "hotfix"
        elif self.name.startswith(("docs/", "doc/")):
            return "documentation"
        elif self.name.startswith(("test/", "tests/")):
            return "testing"

        return None


class GitIntegration:
    """Enhanced Git integration for roadmap workflow support."""

    def __init__(self, repo_path: Optional[Path] = None, config: Optional[object] = None):
        """Initialize Git integration."""
        self.repo_path = repo_path or Path.cwd()
        self._git_dir = self._find_git_directory()
        # Optional roadmap configuration (RoadmapConfig) to influence behavior
        self.config = config

    def _find_git_directory(self) -> Optional[Path]:
        """Find the .git directory by walking up the directory tree."""
        current = self.repo_path.resolve()

        while current != current.parent:
            git_dir = current / ".git"
            if git_dir.exists():
                return git_dir
            current = current.parent

        return None

    def is_git_repository(self) -> bool:
        """Check if current directory is in a Git repository."""
        # Re-check git directory in case the repo was initialized after object creation
        if self._git_dir is None:
            self._git_dir = self._find_git_directory()
        return self._git_dir is not None

    def _run_git_command(
        self, args: List[str], cwd: Optional[Path] = None
    ) -> Optional[str]:
        """Run a git command and return the output."""
        if not self.is_git_repository():
            return None

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def get_current_user(self) -> Optional[str]:
        """Get current Git user name."""
        return self._run_git_command(["config", "user.name"])

    def get_current_email(self) -> Optional[str]:
        """Get current Git user email."""
        return self._run_git_command(["config", "user.email"])

    def get_current_branch(self) -> Optional[GitBranch]:
        """Get information about the current branch."""
        branch_name = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        if not branch_name or branch_name == "HEAD":
            return None

        # Get remote tracking branch
        remote = self._run_git_command(
            ["rev-parse", "--abbrev-ref", f"{branch_name}@{{upstream}}"]
        )

        # Get last commit
        last_commit = self._run_git_command(["rev-parse", "HEAD"])

        return GitBranch(
            name=branch_name, current=True, remote=remote, last_commit=last_commit
        )

    def get_all_branches(self) -> List[GitBranch]:
        """Get all local branches."""
        output = self._run_git_command(["branch", "--format=%(refname:short)|%(HEAD)"])
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

    def get_recent_commits(
        self, count: int = 10, since: Optional[str] = None
    ) -> List[GitCommit]:
        """Get recent commits with detailed information."""
        args = ["log", f"-{count}", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
        if since:
            args.extend(["--since", since])

        output = self._run_git_command(args)
        if not output:
            return []

        commits = []
        for line in output.split("\n"):
            if not line.strip():
                continue

            try:
                hash_val, author, date_str, message = line.split("|", 3)
                date = datetime.fromisoformat(date_str.replace(" ", "T"))

                # Get file statistics for this commit
                stat_output = self._run_git_command(
                    ["show", "--stat", "--format=", hash_val]
                )
                files_changed = []
                insertions = deletions = 0

                if stat_output:
                    for stat_line in stat_output.split("\n"):
                        if " | " in stat_line:
                            file_path = stat_line.split(" | ")[0].strip()
                            files_changed.append(file_path)
                        elif "insertion" in stat_line or "deletion" in stat_line:
                            # Parse lines like: "2 files changed, 15 insertions(+), 3 deletions(-)"
                            numbers = re.findall(r"(\d+) insertion", stat_line)
                            if numbers:
                                insertions = int(numbers[0])
                            numbers = re.findall(r"(\d+) deletion", stat_line)
                            if numbers:
                                deletions = int(numbers[0])

                commits.append(
                    GitCommit(
                        hash=hash_val,
                        author=author,
                        date=date,
                        message=message,
                        files_changed=files_changed,
                        insertions=insertions,
                        deletions=deletions,
                    )
                )
            except (ValueError, IndexError):
                continue

        return commits

    def get_commits_for_issue(
        self, issue_id: str, since: Optional[str] = None
    ) -> List[GitCommit]:
        """Get all commits that reference a specific issue."""
        commits = self.get_recent_commits(count=100, since=since)
        return [
            commit
            for commit in commits
            if issue_id in commit.extract_roadmap_references()
        ]

    def suggest_branch_name(self, issue: Issue) -> str:
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
            if self.config and hasattr(self.config, "defaults"):
                template = self.config.defaults.get("branch_name_template")
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

    def create_branch_for_issue(self, issue: Issue, checkout: bool = True, force: bool = False) -> bool:
        """Create a new branch for an issue.

        Handles edge cases:
        - refuses to create when working tree is dirty (unless force=True)
        - if branch already exists, optionally checks it out
        """
        if not self.is_git_repository():
            return False

        branch_name = self.suggest_branch_name(issue)

        # Check for uncommitted changes
        status_output = self._run_git_command(["status", "--porcelain"]) or ""
        # Consider only substantive changes as dirty: ignore purely untracked files (??)
        status_lines = [l for l in status_output.splitlines() if l.strip()]
        has_substantive_changes = any(not l.startswith("??") for l in status_lines)
        if has_substantive_changes and not force:
            # Working tree has tracked modifications; do not create branch by default
            return False

        # Check if branch already exists
        # Try a couple of rev-parse forms to detect existing local branch
        existing = self._run_git_command(["rev-parse", "--verify", branch_name])
        if not existing:
            existing = self._run_git_command(["rev-parse", "--verify", f"refs/heads/{branch_name}"])
        # If branch exists, optionally checkout it
        if existing:
            if checkout:
                co = self._run_git_command(["checkout", branch_name])
                return co is not None
            else:
                # Branch exists but we are not checking out; success
                return True

        # Remember current branch
        current_branch = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"]) or None

        # Create the branch
        result = self._run_git_command(["checkout", "-b", branch_name])
        if result is None:
            return False

        if not checkout:
            # Switch back to previous branch if we created branch but shouldn't stay on it
            if current_branch:
                self._run_git_command(["checkout", current_branch])

        return True

    def auto_create_issue_from_branch(self, roadmap_core, branch_name: Optional[str] = None) -> Optional[str]:
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
            if roadmap_core.load_issue(existing_issue_id):
                return None  # Issue already exists
            
        # Generate issue details from branch name
        issue_type = branch.suggests_issue_type() or "feature"
        
        # Extract title from branch name
        title = self._extract_title_from_branch_name(branch_name)
        if not title:
            return None
            
        # Create the issue
        try:
            assignee = self.get_current_user() or "Unknown"
            
            content = f"Auto-created from branch: `{branch_name}`\n\nThis issue was automatically created when switching to the branch `{branch_name}`."
            
            issue_data = {
                "title": title,
                "content": content,
                "assignee": assignee,
                "priority": "medium",  # Default priority
                "status": "in_progress",  # Since they're working on it
            }
            
            # Add issue type if the models support it
            if hasattr(roadmap_core, 'create_issue_with_type'):
                issue_data["issue_type"] = issue_type
                
            issue = roadmap_core.create_issue(**issue_data)
            return issue.id
            
        except Exception:
            return None
            
    def _extract_title_from_branch_name(self, branch_name: str) -> Optional[str]:
        """Extract a readable title from a branch name."""
        # Remove common prefixes
        name = branch_name
        prefixes = ["feature/", "bugfix/", "hotfix/", "docs/", "test/", "feat/", "bug/", "fix/"]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
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

    def get_repository_info(self) -> Dict[str, Any]:
        """Get general repository information."""
        if not self.is_git_repository():
            return {}

        info = {}

        # Remote origin URL
        origin_url = self._run_git_command(["config", "--get", "remote.origin.url"])
        if origin_url:
            info["origin_url"] = origin_url

            # Try to extract GitHub repo info
            github_match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", origin_url)
            if github_match:
                info["github_owner"] = github_match.group(1)
                info["github_repo"] = github_match.group(2)

        # Current branch
        current_branch = self.get_current_branch()
        if current_branch:
            info["current_branch"] = current_branch.name

        # Repository root
        repo_root = self._run_git_command(["rev-parse", "--show-toplevel"])
        if repo_root:
            info["repo_root"] = repo_root

        # Total commits
        commit_count = self._run_git_command(["rev-list", "--count", "HEAD"])
        if commit_count:
            info["total_commits"] = int(commit_count)

        return info

    def parse_commit_message_for_updates(self, commit: GitCommit) -> Dict[str, Any]:
        """Parse commit message for roadmap updates."""
        updates = {}

        # Extract progress
        progress = commit.extract_progress_info()
        if progress is not None:
            updates["progress_percentage"] = min(100.0, max(0.0, progress))
            # If progress is set but not 100%, assume work is in progress
            if 0 < progress < 100:
                updates["status"] = "in-progress"

        # Check for completion indicators (enhanced patterns)
        completion_patterns = [
            # Original roadmap patterns
            r"\[closes roadmap:[a-f0-9]{8}\]",
            r"\[fixes roadmap:[a-f0-9]{8}\]",
            # GitHub/GitLab style completion patterns
            r"\b(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#[a-f0-9]{8}",
            # General completion indicators
            r"\b(?:complete|completed|done|finished|finish)\b.*roadmap",
            r"\b(?:close|closes|fix|fixes|resolve|resolves)\b.*roadmap",
        ]

        for pattern in completion_patterns:
            if re.search(pattern, commit.message, re.IGNORECASE):
                updates["status"] = "done"
                updates["progress_percentage"] = 100.0
                break

        # Check for work-in-progress indicators
        wip_patterns = [
            r"\b(?:wip|work in progress|working on)\b",
            r"\[wip\]",
            r"start(?:ed|ing)?.*#[a-f0-9]{8}",
        ]

        for pattern in wip_patterns:
            if re.search(pattern, commit.message, re.IGNORECASE):
                if "status" not in updates:  # Don't override completion status
                    updates["status"] = "in-progress"
                break

        return updates

    def auto_update_issues_from_commits(self, roadmap_core, commits: Optional[List[GitCommit]] = None) -> Dict[str, List[str]]:
        """Automatically update issues based on commit messages.
        
        Args:
            roadmap_core: RoadmapCore instance for issue operations
            commits: List of commits to process. If None, processes recent commits.
            
        Returns:
            Dictionary with 'updated' and 'closed' issue lists
        """
        if commits is None:
            commits = self.get_recent_commits(count=10)
            
        results = {"updated": [], "closed": [], "errors": []}
        
        for commit in commits:
            try:
                # Get referenced issues
                issue_ids = commit.extract_roadmap_references()
                if not issue_ids:
                    continue
                    
                # Parse updates from commit message
                updates = self.parse_commit_message_for_updates(commit)
                if not updates:
                    continue
                    
                for issue_id in issue_ids:
                    try:
                        # Load the issue
                        issue = roadmap_core.get_issue(issue_id)
                        if not issue:
                            results["errors"].append(f"Issue {issue_id} not found")
                            continue
                            
                        # Apply updates
                        update_data = {}
                        if "status" in updates:
                            update_data["status"] = updates["status"]
                        if "progress_percentage" in updates:
                            update_data["progress_percentage"] = updates["progress_percentage"]
                            
                        # Add commit reference to content
                        commit_note = f"\n\n**Auto-updated from commit {commit.short_hash}:** {commit.message}"
                        if issue.content:
                            update_data["content"] = issue.content + commit_note
                        else:
                            update_data["content"] = commit_note.strip()
                        
                        # Add commit to git_commits list if not already present
                        current_commits = issue.git_commits or []
                        commit_ref = {
                            "hash": commit.hash,
                            "message": commit.message,
                            "date": commit.date.isoformat() if commit.date else None
                        }
                        if not any(c.get("hash") == commit.hash for c in current_commits):
                            current_commits.append(commit_ref)
                        update_data["git_commits"] = current_commits
                            
                        # Update the issue
                        roadmap_core.update_issue(issue_id, **update_data)
                        
                        if updates.get("status") == "done":
                            results["closed"].append(issue_id)
                        else:
                            results["updated"].append(issue_id)
                            
                    except Exception as e:
                        results["errors"].append(f"Error updating issue {issue_id}: {str(e)}")
                        
            except Exception as e:
                results["errors"].append(f"Error processing commit {commit.short_hash}: {str(e)}")
                
        return results

    def get_branch_linked_issues(self, branch_name: str) -> List[str]:
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
