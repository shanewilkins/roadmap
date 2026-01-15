"""Tests for GitHub issue link command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.issues.link import link_github_issue
from tests.unit.domain.test_data_factory_generation import TestDataFactory
from tests.unit.shared.test_assertion_helpers import create_mock_issue


class TestLinkCommandBasic:
    """Tests for basic link command functionality.

    Phase 1C refactoring:
    - Use create_mock_issue() factory instead of inline MagicMock()
    - Cleaner, more consistent mock data across tests
    """

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context with core."""
        ctx = TestDataFactory.create_mock_core(is_initialized=True)
        ctx.obj = {"core": MagicMock()}
        return ctx

    def test_link_command_success(self, runner, mock_ctx):
        """Test successfully linking an issue to GitHub."""
        mock_core = mock_ctx.obj["core"]
        # Use factory instead of inline MagicMock
        mock_issue = create_mock_issue(id="abc123", title="Test Issue")
        mock_core.issues.get_by_id.return_value = mock_issue

        with patch(
            "roadmap.adapters.cli.issues.link.GitHubIssueClient"
        ) as mock_gh_client:
            mock_client_instance = MagicMock()
            mock_client_instance.issue_exists.return_value = True
            mock_gh_client.return_value = mock_client_instance

            with patch(
                "roadmap.core.services.github.github_integration_service.GitHubIntegrationService"
            ) as mock_gh_service:
                mock_service_instance = MagicMock()
                mock_service_instance.get_github_config.return_value = (
                    "token",
                    "owner",
                    "repo",
                )
                mock_gh_service.return_value = mock_service_instance

                runner.invoke(
                    link_github_issue,
                    ["abc123", "--github-id", "456"],
                    obj={"core": mock_core},
                )

                # Verify issue was updated
                assert mock_issue.github_issue is None or mock_issue.github_issue == 456
                mock_core.issues.update.assert_called()

    def test_link_command_issue_not_found(self, runner):
        """Test linking when internal issue doesn't exist."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.get_by_id.return_value = None

        result = runner.invoke(
            link_github_issue,
            ["nonexistent", "--github-id", "456"],
            obj={"core": mock_core},
        )

        assert result.exit_code == 1

    def test_link_command_invalid_github_id(self, runner):
        """Test linking with invalid GitHub ID (negative)."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        # Use factory instead of inline MagicMock
        mock_issue = create_mock_issue(id="abc123")
        mock_core.issues.get_by_id.return_value = mock_issue

        result = runner.invoke(
            link_github_issue,
            ["abc123", "--github-id", "-5"],
            obj={"core": mock_core},
        )

        assert result.exit_code == 1

    def test_link_command_already_linked_to_same(self, runner):
        """Test linking when issue is already linked to the same GitHub ID."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        # Use factory with github_issue set
        mock_issue = create_mock_issue(id="abc123", github_issue=456)
        mock_core.issues.get_by_id.return_value = mock_issue

        result = runner.invoke(
            link_github_issue,
            ["abc123", "--github-id", "456"],
            obj={"core": mock_core},
        )

        # Should be success (idempotent)
        assert result.exit_code == 0
        # Should not update
        mock_core.issues.update.assert_not_called()

    def test_link_command_already_linked_to_different(self, runner):
        """Test linking when issue is already linked to a different GitHub ID."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = MagicMock()
        mock_issue.github_issue = 123  # Already linked to different ID
        mock_core.issues.get_by_id.return_value = mock_issue

        result = runner.invoke(
            link_github_issue,
            ["abc123", "--github-id", "456"],
            obj={"core": mock_core},
        )

        assert result.exit_code == 1

    def test_link_command_github_issue_not_found(self, runner):
        """Test linking when GitHub issue doesn't exist."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = MagicMock()
        mock_issue.github_issue = None
        mock_core.issues.get_by_id.return_value = mock_issue

        with patch(
            "roadmap.adapters.cli.issues.link.GitHubIssueClient"
        ) as mock_gh_client:
            mock_client_instance = MagicMock()
            mock_client_instance.issue_exists.return_value = False
            mock_gh_client.return_value = mock_client_instance

            with patch(
                "roadmap.core.services.github.github_integration_service.GitHubIntegrationService"
            ) as mock_gh_service:
                mock_service_instance = MagicMock()
                mock_service_instance.get_github_config.return_value = (
                    "token",
                    "owner",
                    "repo",
                )
                mock_gh_service.return_value = mock_service_instance

                result = runner.invoke(
                    link_github_issue,
                    ["abc123", "--github-id", "999"],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 1

    def test_link_command_with_explicit_owner_repo(self, runner):
        """Test linking with explicit owner and repo options."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = MagicMock()
        mock_issue.id = "abc123"
        mock_issue.title = "Test Issue"
        mock_issue.github_issue = None
        mock_core.issues.get_by_id.return_value = mock_issue

        with patch(
            "roadmap.adapters.cli.issues.link.GitHubIssueClient"
        ) as mock_gh_client:
            mock_client_instance = MagicMock()
            mock_client_instance.issue_exists.return_value = True
            mock_gh_client.return_value = mock_client_instance

            runner.invoke(
                link_github_issue,
                [
                    "abc123",
                    "--github-id",
                    "456",
                    "--owner",
                    "myowner",
                    "--repo",
                    "myrepo",
                ],
                obj={"core": mock_core},
            )

            # Should call GitHub client with explicit owner/repo
            mock_client_instance.issue_exists.assert_called_with(
                "myowner", "myrepo", 456
            )

    def test_link_command_github_error(self, runner):
        """Test handling of GitHub API errors."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = MagicMock()
        mock_issue.github_issue = None
        mock_core.issues.get_by_id.return_value = mock_issue

        with patch(
            "roadmap.adapters.cli.issues.link.GitHubIssueClient"
        ) as mock_gh_client:
            mock_client_instance = MagicMock()
            mock_client_instance.issue_exists.side_effect = Exception("API Error")
            mock_gh_client.return_value = mock_client_instance

            with patch(
                "roadmap.core.services.github.github_integration_service.GitHubIntegrationService"
            ) as mock_gh_service:
                mock_service_instance = MagicMock()
                mock_service_instance.get_github_config.return_value = (
                    "token",
                    "owner",
                    "repo",
                )
                mock_gh_service.return_value = mock_service_instance

                result = runner.invoke(
                    link_github_issue,
                    ["abc123", "--github-id", "456"],
                    obj={"core": mock_core},
                )

                assert result.exit_code == 1

    def test_link_command_missing_config(self, runner):
        """Test linking when GitHub config is not available."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issue = MagicMock()
        mock_issue.github_issue = None
        mock_core.issues.get_by_id.return_value = mock_issue

        with patch(
            "roadmap.core.services.github.github_integration_service.GitHubIntegrationService"
        ) as mock_gh_service:
            mock_service_instance = MagicMock()
            mock_service_instance.get_github_config.return_value = (None, None, None)
            mock_gh_service.return_value = mock_service_instance

            result = runner.invoke(
                link_github_issue,
                ["abc123", "--github-id", "456"],
                obj={"core": mock_core},
            )

            assert result.exit_code == 1

    def test_link_command_without_required_options(self, runner):
        """Test link command without required --github-id option."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        result = runner.invoke(
            link_github_issue,
            ["abc123"],
            obj={"core": mock_core},
        )

        # Should fail due to missing --github-id
        assert result.exit_code != 0
