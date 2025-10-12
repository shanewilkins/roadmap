"""Enhanced GitHub integration for real-time synchronization and CI/CD workflows."""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import requests
from .core import RoadmapCore
from .git_integration import GitIntegration
from .github_client import GitHubClient, GitHubAPIError
from .models import Issue, Status, Priority


class EnhancedGitHubIntegration:
    """Enhanced GitHub integration with real-time sync and CI/CD support."""
    
    def __init__(self, roadmap_core: RoadmapCore, github_client: Optional[GitHubClient] = None):
        """Initialize enhanced GitHub integration."""
        self.core = roadmap_core
        self.git_integration = GitIntegration()
        self.github_client = github_client
        self.sync = None  # Simplified for now - could integrate with existing sync later
        
        # Auto-detect repository info if not provided
        if not self.github_client:
            repo_info = self.git_integration.get_repository_info()
            if "github_owner" in repo_info and "github_repo" in repo_info:
                try:
                    self.github_client = GitHubClient(
                        owner=repo_info["github_owner"],
                        repo=repo_info["github_repo"]
                    )
                    # Simplified sync integration for now
                except GitHubAPIError:
                    # No GitHub token available, continue without sync
                    pass
    
    def is_github_enabled(self) -> bool:
        """Check if GitHub integration is available."""
        return self.github_client is not None
    
    def create_github_issue_from_roadmap(self, roadmap_issue: Issue) -> Optional[Dict[str, Any]]:
        """Create a GitHub issue from a roadmap issue."""
        if not self.is_github_enabled():
            return None
            
        try:
            # Convert roadmap issue to GitHub format
            github_data = {
                "title": roadmap_issue.title,
                "body": self._format_issue_body_for_github(roadmap_issue),
                "labels": self._convert_labels_for_github(roadmap_issue),
                "assignees": self._get_github_assignees(roadmap_issue),
            }
            
            # Add milestone if available
            if roadmap_issue.milestone:
                milestone_number = self._get_github_milestone_number(roadmap_issue.milestone)
                if milestone_number:
                    github_data["milestone"] = milestone_number
            
            # Create the issue
            github_issue = self.github_client.create_issue(**github_data)
            
            # Update roadmap issue with GitHub reference
            self.core.update_issue(
                roadmap_issue.id,
                github_issue=github_issue["number"]
            )
            
            return github_issue
            
        except GitHubAPIError as e:
            print(f"Failed to create GitHub issue: {e}")
            return None
    
    def sync_issue_with_github(self, issue_id: str, direction: str = "bidirectional") -> bool:
        """Sync a specific issue with its GitHub counterpart.
        
        Args:
            issue_id: Roadmap issue ID
            direction: "to_github", "from_github", or "bidirectional"
        """
        if not self.is_github_enabled():
            return False
            
        try:
            roadmap_issue = self.core.get_issue(issue_id)
            if not roadmap_issue:
                return False
                
            # If no GitHub issue linked, create one
            if not roadmap_issue.github_issue:
                if direction in ["to_github", "bidirectional"]:
                    github_issue = self.create_github_issue_from_roadmap(roadmap_issue)
                    return github_issue is not None
                return False
            
            # Get GitHub issue
            github_issue = self.github_client.get_issue(roadmap_issue.github_issue)
            if not github_issue:
                return False
                
            # Perform sync based on direction
            if direction == "to_github":
                return self._update_github_from_roadmap(roadmap_issue, github_issue)
            elif direction == "from_github":
                return self._update_roadmap_from_github(roadmap_issue, github_issue)
            else:  # bidirectional
                # Use timestamp comparison to determine direction
                roadmap_updated = roadmap_issue.updated
                github_updated = datetime.fromisoformat(github_issue["updated_at"].replace("Z", "+00:00"))
                
                if roadmap_updated > github_updated:
                    return self._update_github_from_roadmap(roadmap_issue, github_issue)
                else:
                    return self._update_roadmap_from_github(roadmap_issue, github_issue)
                    
        except Exception as e:
            print(f"Sync failed for issue {issue_id}: {e}")
            return False
    
    def handle_pull_request_event(self, pr_data: Dict[str, Any], action: str) -> List[str]:
        """Handle pull request webhook events.
        
        Args:
            pr_data: Pull request data from webhook
            action: PR action (opened, closed, merged, etc.)
            
        Returns:
            List of updated issue IDs
        """
        updated_issues = []
        
        try:
            # Extract issue references from PR title and body
            pr_title = pr_data.get("title", "")
            pr_body = pr_data.get("body", "") or ""
            pr_number = pr_data.get("number")
            pr_branch = pr_data.get("head", {}).get("ref", "")
            
            # Find referenced issues
            issue_ids = self._extract_issue_references_from_text(pr_title + " " + pr_body)
            
            # Also check branch name for issue references
            if pr_branch:
                from .git_integration import GitBranch
                branch_obj = GitBranch(pr_branch)
                branch_issue_id = branch_obj.extract_issue_id()
                if branch_issue_id:
                    issue_ids.add(branch_issue_id)
            
            # Update issues based on PR action
            for issue_id in issue_ids:
                if self._update_issue_from_pr_event(issue_id, pr_data, action):
                    updated_issues.append(issue_id)
                    
        except Exception as e:
            print(f"Error handling PR event: {e}")
            
        return updated_issues
    
    def handle_push_event(self, push_data: Dict[str, Any]) -> List[str]:
        """Handle push webhook events for commit-based updates.
        
        Args:
            push_data: Push event data from webhook
            
        Returns:
            List of updated issue IDs
        """
        updated_issues = []
        
        try:
            commits = push_data.get("commits", [])
            
            for commit_data in commits:
                message = commit_data.get("message", "")
                commit_hash = commit_data.get("id", "")
                
                # Extract issue references
                issue_ids = self._extract_issue_references_from_text(message)
                
                # Create commit object for processing
                from .git_integration import GitCommit
                commit = GitCommit(
                    hash=commit_hash,
                    author=commit_data.get("author", {}).get("name", ""),
                    date=datetime.fromisoformat(commit_data.get("timestamp", "").replace("Z", "+00:00")),
                    message=message,
                    files_changed=[]
                )
                
                # Update issues based on commit
                for issue_id in issue_ids:
                    if self._update_issue_from_commit_event(issue_id, commit):
                        updated_issues.append(issue_id)
                        
        except Exception as e:
            print(f"Error handling push event: {e}")
            
        return updated_issues
    
    def setup_github_webhook(self, webhook_url: str, events: List[str] = None) -> bool:
        """Set up GitHub webhook for real-time synchronization.
        
        Args:
            webhook_url: URL to receive webhook events
            events: List of events to subscribe to
        """
        if not self.is_github_enabled():
            return False
            
        if events is None:
            events = ["push", "pull_request", "issues", "issue_comment"]
            
        try:
            webhook_data = {
                "name": "web",
                "active": True,
                "events": events,
                "config": {
                    "url": webhook_url,
                    "content_type": "json",
                    "insecure_ssl": "0"
                }
            }
            
            response = self.github_client._make_request(
                "POST",
                f"/repos/{self.github_client.owner}/{self.github_client.repo}/hooks",
                json=webhook_data
            )
            
            return response.status_code == 201
            
        except GitHubAPIError as e:
            print(f"Failed to create webhook: {e}")
            return False
    
    def validate_ci_cd_status(self, issue_id: str) -> Dict[str, Any]:
        """Validate CI/CD status for an issue's associated PR or commit.
        
        Args:
            issue_id: Roadmap issue ID
            
        Returns:
            Dictionary with CI/CD status information
        """
        result = {
            "issue_id": issue_id,
            "has_pr": False,
            "pr_status": None,
            "ci_status": None,
            "checks_passing": False,
            "deployable": False
        }
        
        try:
            issue = self.core.get_issue(issue_id)
            if not issue or not self.is_github_enabled():
                return result
                
            # Find associated PRs
            prs = self._find_prs_for_issue(issue)
            
            if prs:
                result["has_pr"] = True
                pr = prs[0]  # Use the first/most recent PR
                result["pr_status"] = pr.get("state")
                
                # Check CI/CD status
                if pr.get("head"):
                    sha = pr["head"]["sha"]
                    ci_status = self._get_commit_status(sha)
                    result["ci_status"] = ci_status
                    result["checks_passing"] = ci_status.get("state") == "success"
                    result["deployable"] = result["checks_passing"] and pr.get("mergeable", False)
                    
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def enforce_branch_policy(self, branch_name: str) -> Dict[str, Any]:
        """Enforce branch naming and policy requirements.
        
        Args:
            branch_name: Name of the branch to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        try:
            # Check branch naming convention
            from .git_integration import GitBranch
            branch_obj = GitBranch(branch_name)
            
            # Validate branch naming pattern
            if not re.match(r"^(feature|bugfix|hotfix|docs|test)/[a-f0-9]{8}-[\w-]+$", branch_name):
                if not branch_name in ["main", "master", "develop", "dev"]:
                    result["warnings"].append(
                        f"Branch '{branch_name}' doesn't follow recommended naming pattern: type/issueId-description"
                    )
            
            # Check for linked issue
            issue_id = branch_obj.extract_issue_id()
            if issue_id:
                issue = self.core.get_issue(issue_id)
                if not issue:
                    result["errors"].append(f"Branch references non-existent issue: {issue_id}")
                    result["valid"] = False
                elif issue.status == Status.DONE:
                    result["warnings"].append(f"Branch references completed issue: {issue_id}")
            else:
                if not branch_name in ["main", "master", "develop", "dev"]:
                    result["suggestions"].append(
                        "Consider linking this branch to an issue using: feature/issueId-description"
                    )
            
            # Check for merge conflicts (if GitHub integration available)
            if self.is_github_enabled():
                conflict_check = self._check_merge_conflicts(branch_name)
                if conflict_check.get("conflicts"):
                    result["errors"].append("Branch has merge conflicts with main branch")
                    result["valid"] = False
                    
        except Exception as e:
            result["errors"].append(f"Policy validation failed: {e}")
            result["valid"] = False
            
        return result
    
    # Private helper methods
    
    def _format_issue_body_for_github(self, issue: Issue) -> str:
        """Format roadmap issue content for GitHub."""
        body_parts = []
        
        if issue.content:
            body_parts.append(issue.content)
            
        # Add metadata
        metadata = [
            f"**Roadmap ID:** `{issue.id}`",
            f"**Priority:** {issue.priority.value}",
            f"**Assignee:** {issue.assignee}",
        ]
        
        if issue.estimated_hours:
            metadata.append(f"**Estimated Hours:** {issue.estimated_hours}")
            
        if issue.progress_percentage:
            metadata.append(f"**Progress:** {issue.progress_percentage}%")
            
        body_parts.append("\n---\n" + "\n".join(metadata))
        
        return "\n\n".join(body_parts)
    
    def _convert_labels_for_github(self, issue: Issue) -> List[str]:
        """Convert roadmap issue data to GitHub labels."""
        labels = list(issue.labels) if issue.labels else []
        
        # Add priority label
        labels.append(f"priority:{issue.priority.value}")
        
        # Add status label
        labels.append(f"status:{issue.status.value}")
        
        # Add type label if available
        if hasattr(issue, 'issue_type') and issue.issue_type:
            labels.append(f"type:{issue.issue_type}")
            
        return labels
    
    def _get_github_assignees(self, issue: Issue) -> List[str]:
        """Get GitHub assignees from roadmap issue."""
        if not issue.assignee:
            return []
            
        # Try to extract GitHub username from email or use as-is
        assignee = issue.assignee
        if "@" in assignee:
            # Extract username part of email
            assignee = assignee.split("@")[0]
            
        return [assignee]
    
    def _get_github_milestone_number(self, milestone_name: str) -> Optional[int]:
        """Get GitHub milestone number by name."""
        if not self.is_github_enabled():
            return None
            
        try:
            milestones = self.github_client.get_milestones()
            for milestone in milestones:
                if milestone["title"] == milestone_name:
                    return milestone["number"]
        except GitHubAPIError:
            pass
            
        return None
    
    def _extract_issue_references_from_text(self, text: str) -> Set[str]:
        """Extract issue IDs from text using various patterns."""
        patterns = [
            r"\b(?:fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved)\s+#([a-f0-9]{8})\b",
            r"\b(?:addresses?|refs?)\s+#([a-f0-9]{8})\b",
            r"#([a-f0-9]{8})\b",
            r"roadmap:([a-f0-9]{8})\b",
        ]
        
        issue_ids = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            issue_ids.update(matches)
            
        return issue_ids
    
    def _update_github_from_roadmap(self, roadmap_issue: Issue, github_issue: Dict[str, Any]) -> bool:
        """Update GitHub issue from roadmap issue."""
        try:
            update_data = {
                "title": roadmap_issue.title,
                "body": self._format_issue_body_for_github(roadmap_issue),
                "labels": self._convert_labels_for_github(roadmap_issue),
                "state": "closed" if roadmap_issue.status == Status.DONE else "open"
            }
            
            self.github_client.update_issue(roadmap_issue.github_issue, **update_data)
            return True
            
        except GitHubAPIError:
            return False
    
    def _update_roadmap_from_github(self, roadmap_issue: Issue, github_issue: Dict[str, Any]) -> bool:
        """Update roadmap issue from GitHub issue."""
        try:
            # Map GitHub state to roadmap status
            status = Status.DONE if github_issue["state"] == "closed" else Status.IN_PROGRESS
            
            update_data = {
                "title": github_issue["title"],
                "status": status,
            }
            
            # Extract content if body contains roadmap metadata
            body = github_issue.get("body", "")
            if body and "---" in body:
                content = body.split("---")[0].strip()
                if content:
                    update_data["content"] = content
            
            self.core.update_issue(roadmap_issue.id, **update_data)
            return True
            
        except Exception:
            return False
    
    def _update_issue_from_pr_event(self, issue_id: str, pr_data: Dict[str, Any], action: str) -> bool:
        """Update issue based on PR event."""
        try:
            issue = self.core.get_issue(issue_id)
            if not issue:
                return False
                
            update_data = {}
            pr_number = pr_data.get("number")
            pr_url = pr_data.get("html_url")
            
            # Add PR reference to content
            pr_note = f"\n\n**PR #{pr_number}:** {pr_url} ({action})"
            content = (issue.content or "") + pr_note
            update_data["content"] = content
            
            # Update status based on action
            if action == "opened":
                update_data["status"] = "in-progress"
            elif action == "merged":
                update_data["status"] = "done"
                update_data["progress_percentage"] = 100.0
            elif action == "closed" and not pr_data.get("merged", False):
                # PR closed without merging - mark as blocked or keep current status
                pass
                
            self.core.update_issue(issue_id, **update_data)
            return True
            
        except Exception:
            return False
    
    def _update_issue_from_commit_event(self, issue_id: str, commit: Any) -> bool:
        """Update issue based on commit event."""
        try:
            # Use existing git integration logic
            updates = self.git_integration.parse_commit_message_for_updates(commit)
            if not updates:
                return False
                
            issue = self.core.get_issue(issue_id)
            if not issue:
                return False
                
            # Add commit reference to content
            commit_note = f"\n\n**Commit {commit.hash[:8]}:** {commit.message}"
            if issue.content:
                updates["content"] = issue.content + commit_note
            else:
                updates["content"] = commit_note.strip()
                
            self.core.update_issue(issue_id, **updates)
            return True
            
        except Exception:
            return False
    
    def _find_prs_for_issue(self, issue: Issue) -> List[Dict[str, Any]]:
        """Find pull requests associated with an issue."""
        if not self.is_github_enabled():
            return []
            
        try:
            # Search for PRs mentioning the issue ID
            query = f"repo:{self.github_client.owner}/{self.github_client.repo} {issue.id}"
            
            response = self.github_client._make_request("GET", "/search/issues", params={
                "q": query + " type:pr",
                "sort": "updated",
                "order": "desc"
            })
            
            return response.json().get("items", [])
            
        except GitHubAPIError:
            return []
    
    def _get_commit_status(self, sha: str) -> Dict[str, Any]:
        """Get CI/CD status for a commit."""
        if not self.is_github_enabled():
            return {}
            
        try:
            response = self.github_client._make_request(
                "GET",
                f"/repos/{self.github_client.owner}/{self.github_client.repo}/commits/{sha}/status"
            )
            return response.json()
            
        except GitHubAPIError:
            return {}
    
    def _check_merge_conflicts(self, branch_name: str) -> Dict[str, Any]:
        """Check if branch has merge conflicts."""
        if not self.is_github_enabled():
            return {"conflicts": False}
            
        try:
            # Compare branch with main
            response = self.github_client._make_request(
                "GET",
                f"/repos/{self.github_client.owner}/{self.github_client.repo}/compare/main...{branch_name}"
            )
            
            data = response.json()
            return {
                "conflicts": not data.get("mergeable", True),
                "ahead_by": data.get("ahead_by", 0),
                "behind_by": data.get("behind_by", 0)
            }
            
        except GitHubAPIError:
            return {"conflicts": False}