"""Test data factories for consistent and reusable test data generation."""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest

from roadmap.core.domain import Issue, Milestone

# Mark all tests in this file as unit tests (no filesystem operations)
pytestmark = pytest.mark.unit


class TestDataFactory:
    """Factory for generating consistent test data across test suites."""

    @staticmethod
    def issue_id() -> str:
        """Return a unique or generic issue ID for tests."""
        return "ISSUE-123"

    @staticmethod
    def milestone_id() -> str:
        """Return a unique or generic milestone ID for tests."""
        return "MILESTONE-1"

    @staticmethod
    def message() -> str:
        """Return a generic message or title for tests."""
        return "Test message"

    @staticmethod
    def create_mock_core(**kwargs) -> Mock:
        """Create a standardized mock RoadmapCore instance.

        Args:
            **kwargs: Override default mock behavior

        Returns:
            Mock: Configured RoadmapCore mock
        """
        from pathlib import Path

        core = Mock()

        # Set up default behavior
        core.is_initialized.return_value = kwargs.get("is_initialized", True)
        core.root_path = kwargs.get("root_path", Path("/test"))
        core.roadmap_dir = kwargs.get("roadmap_dir", Path("/test/.roadmap"))
        core.issues_dir = kwargs.get("issues_dir", Path("/test/.roadmap/issues"))
        core.milestones_dir = kwargs.get(
            "milestones_dir", Path("/test/.roadmap/milestones")
        )

        # Mock methods with sensible defaults
        core.get_issues.return_value = kwargs.get("issues", [])
        core.get_milestones.return_value = kwargs.get("milestones", [])
        core.add_issue.return_value = kwargs.get(
            "add_issue_return", TestDataFactory.create_mock_issue()
        )
        core.update_issue.return_value = kwargs.get("update_issue_return", True)
        core.delete_issue.return_value = kwargs.get("delete_issue_return", True)
        core.get_issue.return_value = kwargs.get("get_issue_return", None)

        return core

    @staticmethod
    def create_mock_issue(**kwargs) -> Mock:
        """Create a standardized mock Issue instance.

        Args:
            **kwargs: Override default issue properties

        Returns:
            Mock: Configured Issue mock
        """
        issue = Mock(spec=Issue)

        # Set up default properties using TestDataFactory
        issue.id = kwargs.get("id", TestDataFactory.issue_id())
        issue.title = kwargs.get("title", TestDataFactory.message())
        issue.description = kwargs.get("description", TestDataFactory.message())
        issue.status = kwargs.get("status", "open")
        issue.priority = kwargs.get("priority", "medium")
        issue.labels = kwargs.get("labels", [TestDataFactory.message()])
        issue.assignee = kwargs.get("assignee", None)
        issue.milestone_id = kwargs.get("milestone_id", None)
        issue.estimated_hours = kwargs.get("estimated_hours", None)
        issue.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        issue.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
        issue.github_issue_number = kwargs.get("github_issue_number", None)

        return issue

    @staticmethod
    def create_mock_milestone(**kwargs) -> Mock:
        """Create a standardized mock Milestone instance.

        Args:
            **kwargs: Override default milestone properties

        Returns:
            Mock: Configured Milestone mock
        """
        milestone = Mock(spec=Milestone)

        milestone.id = kwargs.get("id", TestDataFactory.milestone_id())
        milestone.title = kwargs.get("title", TestDataFactory.message())
        milestone.description = kwargs.get("description", TestDataFactory.message())
        milestone.due_date = kwargs.get("due_date", None)
        milestone.status = kwargs.get("status", "active")
        milestone.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        milestone.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))

        return milestone

    @staticmethod
    def create_mock_config(**kwargs) -> Mock:
        """Create a standardized mock config instance.

        Args:
            **kwargs: Override default config properties

        Returns:
            Mock: Configured config mock
        """
        config = Mock()

        # Default GitHub configuration
        config.github = kwargs.get(
            "github",
            {
                "owner": "test-owner",
                "repo": "test-repo",
                "token": "test-token",
                "enabled": True,
            },
        )

        # Default project configuration
        config.project = kwargs.get(
            "project",
            {
                "name": "Test Project",
                "version": "1.0.0",
                "description": "Test project description",
            },
        )

        return config

    @staticmethod
    def create_github_webhook_payload(event_type: str, **kwargs) -> dict[str, Any]:
        """Create realistic GitHub webhook payload data.

        Args:
            event_type: Type of GitHub event (issues, push, pull_request, etc.)
            **kwargs: Override default payload properties

        Returns:
            Dict: GitHub webhook payload
        """
        base_payload = {
            "repository": kwargs.get(
                "repository",
                {
                    "name": "test-repo",
                    "full_name": "test-owner/test-repo",
                    "owner": {"login": "test-owner"},
                },
            ),
            "sender": kwargs.get("sender", {"login": "test-user"}),
        }

        if event_type == "issues":
            base_payload.update(
                {
                    "action": kwargs.get("action", "opened"),
                    "issue": kwargs.get(
                        "issue",
                        {
                            "number": 123,
                            "title": "Test Issue",
                            "body": "Test issue description",
                            "labels": [{"name": "bug"}, {"name": "enhancement"}],
                            "assignee": {"login": "assignee-user"},
                            "milestone": {"title": "v1.0"},
                            "state": "open",
                        },
                    ),
                }
            )
        elif event_type == "push":
            base_payload.update(
                {
                    "commits": kwargs.get(
                        "commits",
                        [
                            {
                                "message": "Test commit message",
                                "author": {
                                    "name": "Test User",
                                    "email": "test@example.com",
                                },
                                "id": "abc123",
                                "added": [],
                                "modified": ["file.py"],
                                "removed": [],
                            }
                        ],
                    ),
                    "head_commit": kwargs.get(
                        "head_commit",
                        {"message": "Test commit message", "id": "abc123"},
                    ),
                }
            )
        elif event_type == "pull_request":
            base_payload.update(
                {
                    "action": kwargs.get("action", "opened"),
                    "pull_request": kwargs.get(
                        "pull_request",
                        {
                            "number": 456,
                            "title": "Test Pull Request",
                            "body": "Test PR description",
                            "state": "open",
                            "head": {"sha": "def456"},
                            "base": {"sha": "abc123"},
                        },
                    ),
                }
            )
        elif event_type == "issue_comment":
            base_payload.update(
                {
                    "action": kwargs.get("action", "created"),
                    "comment": kwargs.get(
                        "comment",
                        {"body": "Test comment", "user": {"login": "comment-user"}},
                    ),
                    "issue": kwargs.get(
                        "issue", {"number": 789, "title": "Commented Issue"}
                    ),
                }
            )

        return base_payload

    @staticmethod
    def create_webhook_signature(payload: str, secret: str) -> str:
        """Create GitHub webhook signature for testing.

        Args:
            payload: JSON payload string
            secret: Webhook secret

        Returns:
            str: SHA-256 signature in GitHub format (sha256=...)
        """
        signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @staticmethod
    def create_github_api_response(endpoint: str, **kwargs) -> dict[str, Any]:
        """Create realistic GitHub API response data.

        Args:
            endpoint: API endpoint type (issues, repos, user, etc.)
            **kwargs: Override default response properties

        Returns:
            Dict: GitHub API response data
        """
        if endpoint == "issues":
            return {
                "number": kwargs.get("number", 123),
                "title": kwargs.get("title", "API Issue"),
                "body": kwargs.get("body", "API issue description"),
                "state": kwargs.get("state", "open"),
                "labels": kwargs.get("labels", [{"name": "api-test"}]),
                "assignee": kwargs.get("assignee", None),
                "milestone": kwargs.get("milestone", None),
                "created_at": kwargs.get("created_at", "2023-01-01T00:00:00Z"),
                "updated_at": kwargs.get("updated_at", "2023-01-01T00:00:00Z"),
                "html_url": kwargs.get(
                    "html_url", "https://github.com/test/repo/issues/123"
                ),
            }
        elif endpoint == "repos":
            return {
                "name": kwargs.get("name", "test-repo"),
                "full_name": kwargs.get("full_name", "test-owner/test-repo"),
                "description": kwargs.get("description", "Test repository"),
                "private": kwargs.get("private", False),
                "owner": kwargs.get("owner", {"login": "test-owner"}),
                "default_branch": kwargs.get("default_branch", "main"),
                "html_url": kwargs.get(
                    "html_url", "https://github.com/test-owner/test-repo"
                ),
            }
        elif endpoint == "user":
            return {
                "login": kwargs.get("login", "test-user"),
                "name": kwargs.get("name", "Test User"),
                "email": kwargs.get("email", "test@example.com"),
                "avatar_url": kwargs.get(
                    "avatar_url", "https://github.com/images/test.png"
                ),
            }

        return {}

    @staticmethod
    def create_cli_test_data(**kwargs) -> dict[str, Any]:
        """Create test data for CLI command testing.

        Args:
            **kwargs: Override default CLI test data

        Returns:
            Dict: CLI test data including commands, inputs, and expected outputs
        """
        return {
            "commands": kwargs.get(
                "commands",
                [
                    "roadmap init",
                    'roadmap add "Test Issue"',
                    "roadmap list",
                    "roadmap status",
                ],
            ),
            "inputs": kwargs.get(
                "inputs",
                {
                    "project_name": "Test CLI Project",
                    "owner": "cli-test-owner",
                    "repository": "cli-test-repo",
                },
            ),
            "expected_outputs": kwargs.get(
                "expected_outputs",
                {
                    "init_success": "Roadmap initialized successfully",
                    "add_success": "Issue added successfully",
                    "list_header": "ID",
                    "status_ready": "roadmap is ready",
                },
            ),
        }

    # ========== Error/Exception Fixtures (Phase 10a-c) ==========

    @staticmethod
    def create_validation_error(**kwargs) -> Exception:
        """Create a validation error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                field: Field that failed validation
                value: Invalid value provided

        Returns:
            Exception: Validation error
        """
        message = kwargs.get("message", "Validation failed")
        field = kwargs.get("field", "test_field")
        value = kwargs.get("value", "invalid_value")
        return ValueError(f"{message}: {field}={value}")

    @staticmethod
    def create_permission_error(**kwargs) -> Exception:
        """Create a permission error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                path: Path that failed permission check
                operation: Operation that failed (read/write/execute)

        Returns:
            Exception: Permission error
        """
        message = kwargs.get("message", "Permission denied")
        path = kwargs.get("path", "/test/path")
        operation = kwargs.get("operation", "read")
        return PermissionError(f"{message}: {operation} on {path}")

    @staticmethod
    def create_network_error(**kwargs) -> Exception:
        """Create a network error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                status_code: HTTP status code
                endpoint: API endpoint that failed

        Returns:
            Exception: Network/connection error
        """
        message = kwargs.get("message", "Network error")
        status_code = kwargs.get("status_code", 500)
        endpoint = kwargs.get("endpoint", "https://api.example.com/test")
        return RuntimeError(f"{message}: {status_code} from {endpoint}")

    @staticmethod
    def create_file_not_found_error(**kwargs) -> Exception:
        """Create a file not found error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                path: File path that was not found

        Returns:
            Exception: File not found error
        """
        message = kwargs.get("message", "File not found")
        path = kwargs.get("path", "/test/missing/file.txt")
        return FileNotFoundError(f"{message}: {path}")

    @staticmethod
    def create_timeout_error(**kwargs) -> Exception:
        """Create a timeout error for testing error paths.

        Args:
            **kwargs: Override error properties
                message: Error message
                timeout_seconds: Timeout duration

        Returns:
            Exception: Timeout error
        """
        message = kwargs.get("message", "Operation timed out")
        timeout_seconds = kwargs.get("timeout_seconds", 30)
        return TimeoutError(f"{message} after {timeout_seconds}s")

    @staticmethod
    def create_git_commit(**kwargs) -> Mock:
        """Create a mock Git commit for testing.

        Args:
            **kwargs: Override commit properties
                sha: Commit hash
                message: Commit message
                author: Author name
                timestamp: Commit timestamp
                files: Changed files

        Returns:
            Mock: Configured Git commit object
        """
        from datetime import datetime, timezone

        commit = Mock()
        commit.sha = kwargs.get("sha", "abc123def456")
        commit.message = kwargs.get("message", "Test commit message")
        commit.author = kwargs.get("author", "Test Author")
        commit.timestamp = kwargs.get("timestamp", datetime.now(timezone.utc))
        commit.files = kwargs.get("files", ["file1.py", "file2.py"])
        return commit

    @staticmethod
    def create_git_status(**kwargs) -> Mock:
        """Create a mock Git status for testing.

        Args:
            **kwargs: Override status properties
                branch: Current branch name
                modified: List of modified files
                untracked: List of untracked files
                staged: List of staged files
                is_dirty: Whether working directory is dirty

        Returns:
            Mock: Configured Git status object
        """
        status = Mock()
        status.branch = kwargs.get("branch", "main")
        status.modified = kwargs.get("modified", [])
        status.untracked = kwargs.get("untracked", [])
        status.staged = kwargs.get("staged", [])
        status.is_dirty = kwargs.get("is_dirty", False)
        return status

    @staticmethod
    def create_github_api_error(**kwargs) -> dict[str, Any]:
        """Create a GitHub API error response for testing error paths.

        Args:
            **kwargs: Override error properties
                status_code: HTTP status code
                message: Error message
                error_code: GitHub error code
                documentation_url: Link to docs

        Returns:
            Dict: GitHub API error response
        """
        return {
            "message": kwargs.get("message", "API Error"),
            "status_code": kwargs.get("status_code", 400),
            "error_code": kwargs.get("error_code", "validation_failed"),
            "documentation_url": kwargs.get(
                "documentation_url", "https://docs.github.com/api"
            ),
        }

    @staticmethod
    def create_command_execution_context(**kwargs) -> Mock:
        """Create a command execution context for testing.

        Args:
            **kwargs: Override context properties
                working_dir: Working directory
                environment: Environment variables
                timeout: Execution timeout
                capture_output: Whether to capture output

        Returns:
            Mock: Command execution context
        """
        from pathlib import Path

        context = Mock()
        context.working_dir = kwargs.get("working_dir", Path("/test"))
        context.environment = kwargs.get("environment", {})
        context.timeout = kwargs.get("timeout", 30)
        context.capture_output = kwargs.get("capture_output", True)
        return context
