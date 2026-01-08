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
        """Return a unique or generic issue ID for tests (8 characters)."""
        return "a1b2c3d4"

    @staticmethod
    def milestone_id() -> str:
        """Return a unique or generic milestone ID for tests (8 characters)."""
        return "e5f6g7h8"

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
        issue.content = kwargs.get("content", TestDataFactory.message())
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
        milestone.content = kwargs.get("content", TestDataFactory.message())
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
