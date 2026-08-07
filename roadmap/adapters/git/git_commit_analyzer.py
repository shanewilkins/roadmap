"""Git commit analysis and issue linking."""

import re
from pathlib import Path
from typing import Any

from structlog import get_logger

from roadmap.adapters.git.git import GitCommit
from roadmap.adapters.git.git_command_executor import GitCommandExecutor
from roadmap.common.datetime_parser import parse_datetime

logger = get_logger()


class GitCommitAnalyzer:
    """Analyzes Git commits and links them to roadmap issues."""

    def __init__(self, repo_path: Path | None = None):
        """Initialize commit analyzer."""
        self.executor = GitCommandExecutor(repo_path)
        self.repo_path = repo_path or Path.cwd()

    def _parse_commit_line(self, line: str) -> tuple | None:
        """Parse single commit log line.

        Args:
            line: Commit log line in format: hash|author|date|message

        Returns:
            Tuple of (hash, author, date, message) or None if parsing fails
        """
        if not line.strip():
            return None

        try:
            hash_val, author, date_str, message = line.split("|", 3)
            date = parse_datetime(date_str.replace(" ", "T"), "iso")
            return (hash_val, author, date, message)
        except Exception as e:
            logger.debug("parse_commit_line_failed", line=line, error=str(e))
            return None

    def _extract_file_stats(self, stat_output: str | None) -> tuple[list, int, int]:
        """Extract file changes and insertion/deletion counts from stat output.

        Args:
            stat_output: Git show --stat output

        Returns:
            Tuple of (files_changed list, insertions count, deletions count)
        """
        files_changed = []
        insertions = deletions = 0

        if not stat_output:
            return files_changed, insertions, deletions

        for stat_line in stat_output.split("\n"):
            if " | " in stat_line:
                file_path = stat_line.split(" | ")[0].strip()
                files_changed.append(file_path)
            elif "insertion" in stat_line or "deletion" in stat_line:
                numbers = re.findall(r"(\d+) insertion", stat_line)
                if numbers:
                    insertions = int(numbers[0])
                numbers = re.findall(r"(\d+) deletion", stat_line)
                if numbers:
                    deletions = int(numbers[0])

        return files_changed, insertions, deletions

    def _build_commit_object(
        self,
        hash_val: str,
        author: str,
        date,
        message: str,
        files_changed: list,
        insertions: int,
        deletions: int,
    ) -> GitCommit | None:
        """Build GitCommit object from parsed data.

        Args:
            hash_val: Commit hash
            author: Author name
            date: Commit date
            message: Commit message
            files_changed: List of changed files
            insertions: Number of insertions
            deletions: Number of deletions

        Returns:
            GitCommit object or None if date is invalid
        """
        if date is None:
            return None

        return GitCommit(
            hash=hash_val,
            author=author,
            date=date,
            message=message,
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
        )

    def get_recent_commits(
        self, count: int = 10, since: str | None = None
    ) -> list[GitCommit]:
        """Get recent commits with detailed information.

        Args:
            count: Number of commits to retrieve
            since: Optional date string to filter commits

        Returns:
            List of GitCommit objects
        """
        args = ["log", f"-{count}", "--pretty=format:%H|%an|%ad|%s", "--date=iso"]
        if since:
            args.extend(["--since", since])

        output = self.executor.run(args)
        if not output:
            return []

        commits = []
        for line in output.split("\n"):
            # Parse commit line
            parsed = self._parse_commit_line(line)
            if not parsed:
                continue

            hash_val, author, date, message = parsed

            # Get file statistics
            stat_output = self.executor.run(["show", "--stat", "--format=", hash_val])
            files_changed, insertions, deletions = self._extract_file_stats(stat_output)

            # Build and add commit object
            commit = self._build_commit_object(
                hash_val, author, date, message, files_changed, insertions, deletions
            )
            if commit:
                commits.append(commit)

        return commits

    def get_commits_for_issue(
        self, issue_id: str, since: str | None = None
    ) -> list[GitCommit]:
        """Get all commits that reference a specific issue.

        Args:
            issue_id: Issue ID to search for
            since: Optional date filter

        Returns:
            List of commits referencing the issue
        """
        commits = self.get_recent_commits(count=100, since=since)
        return [
            commit
            for commit in commits
            if issue_id in commit.extract_roadmap_references()
        ]

    def parse_commit_message_for_updates(self, commit: GitCommit) -> dict[str, Any]:
        """Parse commit message for roadmap updates.

        Args:
            commit: GitCommit object to analyze

        Returns:
            Dictionary with potential updates (status, progress_percentage)
        """
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
                updates["status"] = "closed"
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

    def _extract_commit_reference(self, commit: "GitCommit") -> dict:
        """Extract commit reference metadata."""
        return {
            "hash": commit.hash,
            "message": commit.message,
            "date": commit.date.isoformat() if commit.date else None,
        }

    def _build_update_data(self, issue, commit: "GitCommit", updates: dict) -> dict:
        """Build update data from commit and parsed updates."""
        update_data = {}

        # Apply status and progress updates
        if "status" in updates:
            update_data["status"] = updates["status"]
        if "progress_percentage" in updates:
            update_data["progress_percentage"] = updates["progress_percentage"]

        # Add commit reference to content
        commit_note = (
            f"\n\n**Auto-updated from commit {commit.short_hash}:** {commit.message}"
        )
        if issue.content:
            update_data["content"] = issue.content + commit_note
        else:
            update_data["content"] = commit_note.strip()

        # Add commit to git_commits list if not already present
        current_commits = issue.git_commits or []
        commit_ref = self._extract_commit_reference(commit)
        if not any(c.get("hash") == commit.hash for c in current_commits):
            current_commits.append(commit_ref)
        update_data["git_commits"] = current_commits

        return update_data

    def _process_single_issue(
        self,
        roadmap_core,
        issue_id: str,
        commit: "GitCommit",
        updates: dict,
        results: dict,
    ) -> None:
        """Process a single issue update from a commit."""
        try:
            # Load the issue
            issue = roadmap_core.issues.get(issue_id)
            if not issue:
                results["errors"].append(f"Issue {issue_id} not found")
                return

            # Build and apply updates
            update_data = self._build_update_data(issue, commit, updates)
            roadmap_core.issues.update(issue_id, **update_data)

            # Track result
            if updates.get("status") == "closed":
                results["closed"].append(issue_id)
            else:
                results["updated"].append(issue_id)

        except Exception as e:
            results["errors"].append(f"Error updating issue {issue_id}: {str(e)}")

    def _process_commit_issues(
        self, roadmap_core, commit: "GitCommit", results: dict
    ) -> None:
        """Process all issues referenced in a commit."""
        try:
            # Get referenced issues
            issue_ids = commit.extract_roadmap_references()
            if not issue_ids:
                return

            # Parse updates from commit message
            updates = self.parse_commit_message_for_updates(commit)
            if not updates:
                return

            # Update each issue
            for issue_id in issue_ids:
                self._process_single_issue(
                    roadmap_core, issue_id, commit, updates, results
                )

        except Exception as e:
            results["errors"].append(
                f"Error processing commit {commit.short_hash}: {str(e)}"
            )

    def auto_update_issues_from_commits(
        self, roadmap_core, commits: list["GitCommit"] | None = None
    ) -> dict[str, list[str]]:
        """Automatically update issues based on commit messages.

        Args:
            roadmap_core: RoadmapCore instance for issue operations
            commits: List of commits to process. If None, processes recent commits.

        Returns:
            Dictionary with 'updated', 'closed', and 'errors' lists
        """
        if commits is None:
            commits = self.get_recent_commits(count=10)

        results = {"updated": [], "closed": [], "errors": []}

        for commit in commits:
            self._process_commit_issues(roadmap_core, commit, results)

        return results
