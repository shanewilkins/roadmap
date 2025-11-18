"""
Comprehensive tests for Enhanced GitHub Integration module.

This module tests the enhanced GitHub integration functionality including:
- Real-time synchronization with GitHub
- Webhook event handling (PR, push, issues)
- CI/CD status validation
- Branch policy enforcement
- Issue creation and bidirectional sync
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from roadmap.enhanced_github_integration import EnhancedGitHubIntegration
from roadmap.infrastructure.github import GitHubAPIError, GitHubClient
from roadmap.domain import Issue, Priority, Status

pytestmark = pytest.mark.unit


class TestEnhancedGitHubIntegrationInitialization:
    """Test initialization and basic functionality."""

    def test_initialization_with_github_client(self, mock_core):
        """Test initialization with provided GitHub client."""
        mock_github_client = Mock(spec=GitHubClient)
        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)

        assert integration.core == mock_core
        assert integration.github_client == mock_github_client
        assert integration.is_github_enabled() is True

    def test_initialization_without_github_client(self, mock_core):
        """Test initialization without GitHub client."""
        with patch(
            "roadmap.enhanced_github_integration.GitIntegration"
        ) as mock_git_integration:
            mock_git_integration.return_value.get_repository_info.return_value = {}

            integration = EnhancedGitHubIntegration(mock_core)

            assert integration.core == mock_core
            assert integration.github_client is None
            assert integration.is_github_enabled() is False

    def test_initialization_with_auto_detection(self, mock_core):
        """Test initialization with automatic GitHub client detection."""
        repo_info = {"github_owner": "test-owner", "github_repo": "test-repo"}

        with patch(
            "roadmap.enhanced_github_integration.GitIntegration"
        ) as mock_git_integration:
            mock_git_integration.return_value.get_repository_info.return_value = (
                repo_info
            )

            with patch(
                "roadmap.enhanced_github_integration.GitHubClient"
            ) as mock_github_client_class:
                mock_client = Mock()
                mock_github_client_class.return_value = mock_client

                integration = EnhancedGitHubIntegration(mock_core)

                assert integration.github_client == mock_client
                mock_github_client_class.assert_called_once_with(
                    owner="test-owner", repo="test-repo"
                )

    def test_initialization_with_github_api_error(self, mock_core):
        """Test initialization when GitHub client creation fails."""
        repo_info = {"github_owner": "test-owner", "github_repo": "test-repo"}

        with patch(
            "roadmap.enhanced_github_integration.GitIntegration"
        ) as mock_git_integration:
            mock_git_integration.return_value.get_repository_info.return_value = (
                repo_info
            )

            with patch(
                "roadmap.enhanced_github_integration.GitHubClient"
            ) as mock_github_client_class:
                mock_github_client_class.side_effect = GitHubAPIError("No token")

                integration = EnhancedGitHubIntegration(mock_core)

                assert integration.github_client is None
                assert integration.is_github_enabled() is False


class TestGitHubIssueCreation:
    """Test GitHub issue creation from roadmap issues."""

    @pytest.fixture
    def mock_integration(self, mock_core):
        """Create integration with mocked GitHub client."""
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.owner = "test-owner"
        mock_github_client.repo = "test-repo"
        return EnhancedGitHubIntegration(mock_core, mock_github_client)

    @pytest.fixture
    def sample_issue(self):
        """Create a sample roadmap issue for testing."""
        return Issue(
            id="test123",
            title="Test Issue",
            content="Test issue content",
            priority=Priority.HIGH,
            status=Status.TODO,
            assignee="test-user",
            estimated_hours=5.0,
        )

    def test_create_github_issue_success(self, mock_integration, sample_issue):
        """Test successful GitHub issue creation."""
        github_issue_data = {
            "id": 123,
            "number": 456,
            "title": "Test Issue",
            "body": "Test issue content",
            "state": "open",
        }

        mock_integration.github_client.create_issue.return_value = github_issue_data

        result = mock_integration.create_github_issue_from_roadmap(sample_issue)

        assert result == github_issue_data
        mock_integration.github_client.create_issue.assert_called_once()

        # Verify issue data was formatted correctly
        call_args = mock_integration.github_client.create_issue.call_args[1]
        assert call_args["title"] == "Test Issue"
        assert "Test issue content" in call_args["body"]
        assert "**Roadmap ID:** `test123`" in call_args["body"]

    def test_create_github_issue_without_client(self, mock_core, sample_issue):
        """Test issue creation when GitHub client is not available."""
        integration = EnhancedGitHubIntegration(mock_core, None)

        result = integration.create_github_issue_from_roadmap(sample_issue)

        assert result is None

    def test_create_github_issue_api_error(self, mock_integration, sample_issue):
        """Test GitHub issue creation with API error."""
        mock_integration.github_client.create_issue.side_effect = GitHubAPIError(
            "API error"
        )

        result = mock_integration.create_github_issue_from_roadmap(sample_issue)

        assert result is None

    def test_format_issue_body_for_github(self, mock_integration, sample_issue):
        """Test issue body formatting for GitHub."""
        formatted_body = mock_integration._format_issue_body_for_github(sample_issue)

        assert "Test issue content" in formatted_body
        assert "**Roadmap ID:** `test123`" in formatted_body
        assert "**Priority:** high" in formatted_body
        assert "**Assignee:** test-user" in formatted_body
        assert "**Estimated Hours:** 5.0" in formatted_body

    def test_convert_labels_for_github(self, mock_integration, sample_issue):
        """Test label conversion for GitHub."""
        labels = mock_integration._convert_labels_for_github(sample_issue)

        # Check that expected labels are present (implementation may include additional ones)
        assert "priority:high" in labels
        assert "status:todo" in labels
        assert any(
            "type:" in label for label in labels
        )  # Check for type label presence    def test_get_github_assignees(self, mock_integration):
        """Test GitHub assignee extraction."""
        # Test with email
        issue_with_email = Issue(
            id="test1",
            title="Test",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="user@example.com",
        )
        assignees = mock_integration._get_github_assignees(issue_with_email)
        assert assignees == ["user"]

        # Test with username
        issue_with_username = Issue(
            id="test2",
            title="Test",
            priority=Priority.MEDIUM,
            status=Status.TODO,
            assignee="username",
        )
        assignees = mock_integration._get_github_assignees(issue_with_username)
        assert assignees == ["username"]

        # Test without assignee
        issue_no_assignee = Issue(
            id="test3", title="Test", priority=Priority.MEDIUM, status=Status.TODO
        )
        assignees = mock_integration._get_github_assignees(issue_no_assignee)
        assert assignees == []


class TestIssueSynchronization:
    """Test bidirectional issue synchronization."""

    @pytest.fixture
    def mock_integration_with_setup(self, mock_core):
        """Create integration with fully mocked dependencies."""
        mock_github_client = Mock(spec=GitHubClient)
        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)
        return integration

    def test_sync_issue_to_github_new_issue(
        self, mock_integration_with_setup, mock_issue
    ):
        """Test syncing new roadmap issue to GitHub."""
        # Set up mock issue with required attributes
        mock_issue.github_issue = None
        mock_issue.content = "Test content"
        mock_issue.title = "Test Issue"
        mock_issue.priority = Priority.HIGH
        mock_issue.status = Status.TODO
        mock_issue.assignee = "test-user"
        mock_issue.progress_percentage = 0
        mock_issue.milestone = None
        mock_integration_with_setup.core.get_issue.return_value = mock_issue

        github_issue_data = {"id": 123, "number": 456}
        mock_integration_with_setup.github_client.create_issue.return_value = (
            github_issue_data
        )

        result = mock_integration_with_setup.sync_issue_with_github(
            "test123", "to_github"
        )

        assert result is True
        mock_integration_with_setup.github_client.create_issue.assert_called_once()

    def test_sync_issue_from_github_existing_issue(
        self, mock_integration_with_setup, mock_issue
    ):
        """Test syncing existing GitHub issue to roadmap."""
        mock_integration_with_setup.core.get_issue.return_value = mock_issue
        mock_issue.github_issue = 456  # Already linked to GitHub

        github_issue_data = {
            "id": 123,
            "number": 456,
            "title": "Updated Title",
            "body": "Updated content",
            "state": "open",
        }
        mock_integration_with_setup.github_client.get_issue.return_value = (
            github_issue_data
        )

        result = mock_integration_with_setup.sync_issue_with_github(
            "test123", "from_github"
        )

        assert result is True
        mock_integration_with_setup.github_client.get_issue.assert_called_once_with(456)

    def test_sync_issue_bidirectional(self, mock_integration_with_setup, mock_issue):
        """Test bidirectional sync with conflict detection."""
        from datetime import timezone

        # Set up mock issue with required attributes
        mock_issue.github_issue = 456
        mock_issue.updated = datetime.now(timezone.utc)
        mock_issue.content = "Test content"
        mock_issue.title = "Test Issue"
        mock_integration_with_setup.core.get_issue.return_value = mock_issue

        github_issue_data = {
            "id": 123,
            "number": 456,
            "title": "GitHub Title",
            "body": "GitHub content",
            "state": "open",
            "updated_at": "2023-01-01T12:00:00Z",
        }
        mock_integration_with_setup.github_client.get_issue.return_value = (
            github_issue_data
        )

        result = mock_integration_with_setup.sync_issue_with_github(
            "test123", "bidirectional"
        )

        assert result is True

    def test_sync_issue_without_github_client(self, mock_core, mock_issue):
        """Test sync when GitHub client is not available."""
        integration = EnhancedGitHubIntegration(mock_core, None)

        result = integration.sync_issue_with_github("test123")

        assert result is False

    def test_sync_nonexistent_issue(self, mock_integration_with_setup):
        """Test sync with nonexistent roadmap issue."""
        mock_integration_with_setup.core.get_issue.return_value = None

        result = mock_integration_with_setup.sync_issue_with_github("nonexistent")

        assert result is False


class TestWebhookEventHandling:
    """Test webhook event processing."""

    @pytest.fixture
    def mock_integration(self, mock_core):
        """Create integration for webhook testing."""
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.owner = "test-owner"
        mock_github_client.repo = "test-repo"
        mock_github_client._make_request = Mock()
        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)
        return integration

    @pytest.fixture
    def sample_pr_data(self):
        """Sample pull request webhook data."""
        return {
            "number": 123,
            "title": "Fix issue abc12345",
            "body": "This PR fixes issue #abc12345 and closes #def67890",
            "state": "open",
            "head": {"ref": "feature/abc12345-fix-bug", "sha": "abc123def456"},
            "base": {"ref": "main"},
        }

    @pytest.fixture
    def sample_push_data(self):
        """Sample push webhook data."""
        return {
            "ref": "refs/heads/feature/abc12345-new-feature",
            "commits": [
                {
                    "id": "commit1",
                    "message": "Work on issue #abc12345",
                    "author": {"name": "Test User"},
                    "timestamp": "2023-01-01T12:00:00Z",
                },
                {
                    "id": "commit2",
                    "message": "Complete roadmap:abc12345 implementation",
                    "author": {"name": "Test User"},
                    "timestamp": "2023-01-01T12:30:00Z",
                },
            ],
        }

    def test_handle_pull_request_opened(self, mock_integration, sample_pr_data):
        """Test handling pull request opened event."""
        mock_integration.core.get_issue.return_value = Mock(id="abc12345")
        with patch.object(
            mock_integration, "_update_issue_from_pr_event", return_value=True
        ):
            result = mock_integration.handle_pull_request_event(
                sample_pr_data, "opened"
            )

            assert "abc12345" in result
        assert len(result) >= 1

    def test_handle_pull_request_merged(self, mock_integration, sample_pr_data):
        """Test handling pull request merged event."""
        mock_issue = Mock(id="abc12345", status=Status.IN_PROGRESS)
        mock_integration.core.get_issue.return_value = mock_issue
        sample_pr_data["merged"] = True
        with patch.object(
            mock_integration, "_update_issue_from_pr_event", return_value=True
        ):
            result = mock_integration.handle_pull_request_event(
                sample_pr_data, "closed"
            )

            assert "abc12345" in result
        # Should update issue status when PR is merged

    def test_handle_push_event(self, mock_integration, sample_push_data):
        """Test handling push event."""
        mock_issue = Mock(id="abc12345")
        mock_integration.core.get_issue.return_value = mock_issue
        with patch.object(
            mock_integration, "_update_issue_from_commit_event", return_value=True
        ):
            result = mock_integration.handle_push_event(sample_push_data)

            assert "abc12345" in result

    def test_extract_issue_references_from_text(self, mock_integration):
        """Test issue reference extraction from text."""
        text = "Fix issue #abc12345 and resolve #def67890. Also fixes roadmap:12ab34cd"

        references = mock_integration._extract_issue_references_from_text(text)

        expected = {"abc12345", "def67890", "12ab34cd"}
        assert references == expected

    def test_webhook_setup_success(self, mock_integration):
        """Test successful webhook setup."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_integration.github_client._make_request.return_value = mock_response

        result = mock_integration.setup_github_webhook("https://example.com/webhook")

        assert result is True
        mock_integration.github_client._make_request.assert_called_once()

    def test_webhook_setup_failure(self, mock_integration):
        """Test webhook setup failure."""
        mock_integration.github_client._make_request.side_effect = GitHubAPIError(
            "Failed"
        )

        result = mock_integration.setup_github_webhook("https://example.com/webhook")

        assert result is False

    def test_webhook_setup_without_github_client(self, mock_core):
        """Test webhook setup when GitHub client is not available."""
        with patch(
            "roadmap.enhanced_github_integration.GitIntegration"
        ) as mock_git_integration:
            mock_git_integration.return_value.get_repository_info.return_value = {}
            integration = EnhancedGitHubIntegration(mock_core, None)

            result = integration.setup_github_webhook("https://example.com/webhook")

            assert result is False


class TestCICDStatusValidation:
    """Test CI/CD status validation functionality."""

    @pytest.fixture
    def mock_integration(self, mock_core):
        """Create integration for CI/CD testing."""
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.owner = "test-owner"
        mock_github_client.repo = "test-repo"
        mock_github_client._make_request = Mock()
        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)
        return integration

    def test_validate_ci_cd_status_with_pr(self, mock_integration, mock_issue):
        """Test CI/CD status validation with associated PR."""
        mock_integration.core.get_issue.return_value = mock_issue

        pr_data = [
            {
                "number": 123,
                "state": "open",
                "head": {"sha": "abc123"},
                "mergeable": True,
            }
        ]
        with patch.object(
            mock_integration, "_find_prs_for_issue", return_value=pr_data
        ):
            ci_status = {"state": "success", "statuses": []}
            with patch.object(
                mock_integration, "_get_commit_status", return_value=ci_status
            ):
                result = mock_integration.validate_ci_cd_status("test123")

                assert result["issue_id"] == "test123"
                assert result["has_pr"] is True
                assert result["checks_passing"] is True
                assert result["deployable"] is True

    def test_validate_ci_cd_status_failing_checks(self, mock_integration, mock_issue):
        """Test CI/CD status validation with failing checks."""
        mock_integration.core.get_issue.return_value = mock_issue

        pr_data = [
            {
                "number": 123,
                "state": "open",
                "head": {"sha": "abc123"},
                "mergeable": True,
            }
        ]
        with patch.object(
            mock_integration, "_find_prs_for_issue", return_value=pr_data
        ):
            ci_status = {"state": "failure", "statuses": []}
            with patch.object(
                mock_integration, "_get_commit_status", return_value=ci_status
            ):
                result = mock_integration.validate_ci_cd_status("test123")

                assert result["checks_passing"] is False
                assert result["deployable"] is False

    def test_validate_ci_cd_status_no_pr(self, mock_integration, mock_issue):
        """Test CI/CD status validation without associated PR."""
        mock_integration.core.get_issue.return_value = mock_issue
        with patch.object(mock_integration, "_find_prs_for_issue", return_value=[]):
            result = mock_integration.validate_ci_cd_status("test123")

            assert result["has_pr"] is False
            assert result["deployable"] is False

    def test_get_commit_status(self, mock_integration):
        """Test commit status retrieval."""
        status_data = {
            "state": "success",
            "statuses": [
                {"state": "success", "context": "ci/test"},
                {"state": "success", "context": "ci/build"},
            ],
        }

        mock_response = Mock()
        mock_response.json.return_value = status_data
        mock_integration.github_client._make_request.return_value = mock_response

        result = mock_integration._get_commit_status("abc123")

        assert result == status_data

    def test_find_prs_for_issue(self, mock_integration, mock_issue):
        """Test finding PRs associated with an issue."""
        mock_integration.github_client.owner = "test-owner"
        mock_integration.github_client.repo = "test-repo"

        search_results = {
            "items": [
                {"number": 123, "title": "Fix test123"},
                {"number": 124, "title": "Another PR"},
            ]
        }

        mock_response = Mock()
        mock_response.json.return_value = search_results
        mock_integration.github_client._make_request.return_value = mock_response

        result = mock_integration._find_prs_for_issue(mock_issue)

        assert len(result) == 2
        assert result[0]["number"] == 123


class TestBranchPolicyEnforcement:
    """Test branch policy enforcement functionality."""

    @pytest.fixture
    def mock_integration(self, mock_core):
        """Create integration for branch policy testing."""
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.owner = "test-owner"
        mock_github_client.repo = "test-repo"
        mock_github_client._make_request = Mock()
        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)
        return integration

    def test_enforce_branch_policy_valid_branch(self, mock_integration):
        """Test branch policy validation for valid branch."""
        mock_integration.core.get_issue.return_value = Mock(
            id="abc12345", status=Status.IN_PROGRESS
        )
        with patch.object(
            mock_integration,
            "_check_merge_conflicts",
            return_value={"conflicts": False},
        ):
            result = mock_integration.enforce_branch_policy(
                "feature/abc12345-new-feature"
            )

            # Valid branch should pass despite any warnings
            assert len(result["errors"]) == 0
        assert len(result["errors"]) == 0

    def test_enforce_branch_policy_invalid_naming(self, mock_integration):
        """Test branch policy validation for invalid naming."""
        result = mock_integration.enforce_branch_policy("random-branch-name")

        assert len(result["warnings"]) > 0
        assert "naming pattern" in result["warnings"][0]

    def test_enforce_branch_policy_nonexistent_issue(self, mock_integration):
        """Test branch policy with nonexistent issue reference."""
        mock_integration.core.get_issue.return_value = None

        result = mock_integration.enforce_branch_policy("feature/abc12345-test")

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_enforce_branch_policy_completed_issue(self, mock_integration):
        """Test branch policy with completed issue reference."""
        mock_integration.core.get_issue.return_value = Mock(
            id="abc12345", status=Status.DONE
        )
        with patch.object(
            mock_integration,
            "_check_merge_conflicts",
            return_value={"conflicts": False},
        ):
            result = mock_integration.enforce_branch_policy(
                "feature/abc12345-new-feature"
            )

            assert len(result["warnings"]) > 0
            assert any("completed issue" in warning for warning in result["warnings"])

    def test_check_merge_conflicts(self, mock_integration):
        """Test merge conflict detection."""
        compare_data = {"mergeable": False, "ahead_by": 5, "behind_by": 2}

        mock_response = Mock()
        mock_response.json.return_value = compare_data
        mock_integration.github_client._make_request.return_value = mock_response

        result = mock_integration._check_merge_conflicts("feature/test-branch")

        assert result["conflicts"] is True
        assert result["ahead_by"] == 5
        assert result["behind_by"] == 2


class TestIntegrationErrorHandling:
    """Test error handling and edge cases."""

    def test_github_api_error_handling(self, mock_core):
        """Test handling of various GitHub API errors."""
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.create_issue.side_effect = GitHubAPIError(
            "Rate limit exceeded"
        )

        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)

        issue = Issue(
            id="test123", title="Test", priority=Priority.MEDIUM, status=Status.TODO
        )

        result = integration.create_github_issue_from_roadmap(issue)
        assert result is None

    def test_network_error_handling(self, mock_core):
        """Test handling of network errors."""
        mock_github_client = Mock(spec=GitHubClient)
        mock_github_client.owner = "test-owner"
        mock_github_client.repo = "test-repo"
        mock_github_client._make_request.side_effect = (
            requests.exceptions.ConnectionError()
        )

        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)

        # ConnectionError should be raised since implementation doesn't catch it
        with pytest.raises(requests.exceptions.ConnectionError):
            integration.setup_github_webhook("https://example.com/webhook")

    def test_malformed_webhook_data_handling(self, mock_core):
        """Test handling of malformed webhook data."""
        mock_github_client = Mock(spec=GitHubClient)
        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)

        # Test with missing required fields
        malformed_pr_data = {"title": "Test PR"}  # Missing number, state, etc.

        result = integration.handle_pull_request_event(malformed_pr_data, "opened")

        # Should handle gracefully and return empty list
        assert result == []

    def test_empty_webhook_events(self, mock_core):
        """Test handling of empty webhook events."""
        mock_github_client = Mock(spec=GitHubClient)
        integration = EnhancedGitHubIntegration(mock_core, mock_github_client)

        # Test empty PR event
        result = integration.handle_pull_request_event({}, "opened")
        assert result == []

        # Test empty push event
        result = integration.handle_push_event({})
        assert result == []


# Add integration tests that require more complex setup
class TestRealWorldScenarios:
    """Test realistic integration scenarios."""

    def test_complete_issue_workflow(self, mock_core):
        """Test complete issue workflow from creation to completion."""
        # This would test a full workflow:
        # 1. Create roadmap issue
        # 2. Sync to GitHub
        # 3. Create PR
        # 4. Handle PR events
        # 5. Merge PR
        # 6. Update issue status
        pass  # Placeholder for comprehensive workflow test

    def test_conflict_resolution_workflow(self, mock_core):
        """Test conflict resolution between roadmap and GitHub."""
        # Test scenario where both roadmap and GitHub issue are updated
        # and need conflict resolution
        pass  # Placeholder for conflict resolution test

    def test_webhook_event_chain(self, mock_core):
        """Test chain of webhook events (push -> PR -> merge)."""
        # Test realistic sequence of webhook events
        pass  # Placeholder for webhook chain test
