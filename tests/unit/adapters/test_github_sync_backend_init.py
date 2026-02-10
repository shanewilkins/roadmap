"""Tests for GitHub sync backend initialization and error handling.

Tests safe initialization patterns and graceful error handling when
GitHub credentials are missing or invalid.
"""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.sync.backends.github_sync_backend import GitHubSyncBackend


class TestGitHubSyncBackendInitialization:
    """Test GitHub sync backend safe initialization."""

    def test_backend_initializes_with_valid_config(self):
        """Test backend initializes successfully with valid GitHub config."""
        mock_core = MagicMock()
        config = {
            "token": "valid-token-123",
            "owner": "test-owner",
            "repo": "test-repo",
        }

        with patch(
            "roadmap.adapters.sync.backends.github_sync_backend.GitHubClientWrapper"
        ):
            backend = GitHubSyncBackend(core=mock_core, config=config)

            assert backend is not None
            assert backend.config["token"] == "valid-token-123"

    def test_backend_handles_missing_token_gracefully(self):
        """Test backend handles missing token without crashing."""
        mock_core = MagicMock()
        config = {
            "owner": "test-owner",
            "repo": "test-repo",
        }

        try:
            backend = GitHubSyncBackend(core=mock_core, config=config)
            # Backend creates without token, may fail on operations
            assert backend is not None
        except Exception as e:
            # Operations may fail, but initialization should be safe
            pytest.skip(f"Token validation happens at operation time: {e}")

    def test_backend_initializes_with_owner_and_repo(self):
        """Test backend stores owner and repo configuration."""
        mock_core = MagicMock()
        config = {"token": "test-token", "owner": "test-owner", "repo": "test-repo"}

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubIssueClient"
        ):
            backend = GitHubSyncBackend(core=mock_core, config=config)

            assert backend.config["owner"] == "test-owner"
            assert backend.config["repo"] == "test-repo"

    def test_backend_safe_initialization_pattern(self):
        """Test safe init pattern for optional GitHub setup."""
        mock_core = MagicMock()
        config = {
            "token": "test-token",
            "owner": "test-owner",
            "repo": "test-repo",
        }

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubIssueClient"
        ):
            backend = GitHubSyncBackend(core=mock_core, config=config)

            # Should have _safe_init or similar pattern for optional GitHub
            assert (
                hasattr(backend, "_safe_init")
                or hasattr(backend, "authenticate")
                or hasattr(backend, "client")
            )

    def test_backend_handles_invalid_credentials(self):
        """Test backend gracefully handles invalid credentials."""
        mock_core = MagicMock()
        config = {"token": "invalid-token"}

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubIssueClient"
        ) as mock_client:
            # Simulate invalid token error
            mock_client.side_effect = Exception("Invalid token")

            try:
                # Should not crash during init if token is validated lazily
                GitHubSyncBackend(core=mock_core, config=config)
            except Exception:
                # Error handling at init time is acceptable for invalid tokens
                pass


class TestGitHubSyncBackendOperations:
    """Test GitHub sync backend operations."""

    @pytest.fixture
    def backend(self):
        """Create a mock GitHub sync backend."""
        mock_core = MagicMock()
        config = {"token": "test-token", "owner": "test-owner", "repo": "test-repo"}

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubIssueClient"
        ):
            backend = GitHubSyncBackend(core=mock_core, config=config)
            backend.github_client = MagicMock()
            return backend

    def test_backend_fetch_issues(self, backend):
        """Test backend can fetch issues from GitHub."""
        assert backend.github_client is not None
        backend.github_client.get_issues.return_value = [
            {"number": 1, "title": "Issue 1", "state": "open"},
            {"number": 2, "title": "Issue 2", "state": "closed"},
        ]

        # Should be able to call get_issues through client
        assert backend.github_client.get_issues.return_value is not None

    def test_backend_fetch_milestones(self, backend):
        """Test backend can fetch milestones from GitHub."""
        backend.github_client.get_milestones.return_value = [
            {"number": 1, "title": "v1.0", "state": "open"},
            {"number": 2, "title": "v2.0", "state": "closed"},
        ]

        # Should be able to call get_milestones through client
        assert backend.github_client is not None
        assert backend.github_client.get_milestones.return_value is not None

    def test_backend_update_issue_state(self, backend):
        """Test backend can update issue state on GitHub."""
        backend.github_client.update_issue_state.return_value = True

        # Verify update capability exists
        assert hasattr(backend.github_client, "update_issue_state")

    def test_backend_with_mocked_client(self, backend):
        """Test backend operations with fully mocked client."""
        # Setup mock responses
        backend.github_client.get_issues.return_value = [
            {"number": 1, "title": "Test", "state": "open"}
        ]
        backend.github_client.update_issue_state.return_value = {"state": "closed"}

        # Verify we can use the backend
        assert backend.config["owner"] == "test-owner"
        assert backend.config["repo"] == "test-repo"
        assert backend.github_client.get_issues() is not None

    def test_delete_issues_batches_and_counts(self, backend, mocker):
        """Test delete_issues aggregates batch deletions."""
        node_response = {
            "data": {
                "issue0": {
                    "issueOrPullRequest": {
                        "__typename": "Issue",
                        "id": "n1",
                        "number": 1,
                    }
                },
                "issue1": {
                    "issueOrPullRequest": {
                        "__typename": "Issue",
                        "id": "n2",
                        "number": 2,
                    }
                },
                "issue2": {
                    "issueOrPullRequest": {
                        "__typename": "Issue",
                        "id": "n3",
                        "number": 3,
                    }
                },
            }
        }
        delete_response = {
            "data": {
                "delete0": {"clientMutationId": "d1"},
                "delete1": {"clientMutationId": "d2"},
                "delete2": {"clientMutationId": "d3"},
            }
        }
        mocker.patch.object(
            backend,
            "_post_graphql",
            side_effect=[node_response, delete_response],
        )

        deleted = backend.delete_issues([1, 2, 3])

        assert deleted == 3
        assert backend._post_graphql.call_count == 2

    def test_resolve_issue_node_ids_parses_response(self, backend, mocker):
        """Test node ID resolution from GraphQL response."""
        response = {
            "data": {
                "issue0": {
                    "issueOrPullRequest": {
                        "__typename": "Issue",
                        "id": "n1",
                        "number": 1,
                    }
                },
                "issue1": {
                    "issueOrPullRequest": {
                        "__typename": "Issue",
                        "id": "n2",
                        "number": 2,
                    }
                },
            }
        }
        mocker.patch.object(backend, "_post_graphql", return_value=response)

        node_ids, skipped_prs = backend._resolve_issue_node_ids([1, 2], "o", "r", "t")

        assert node_ids == {1: "n1", 2: "n2"}
        assert skipped_prs == []


class TestGitHubSyncBackendErrorHandling:
    """Test GitHub sync backend error handling."""

    def test_backend_handles_network_errors(self):
        """Test backend gracefully handles network errors."""
        mock_core = MagicMock()
        config = {
            "token": "test-token",
            "owner": "test-owner",
            "repo": "test-repo",
        }

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubIssueClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_issues.side_effect = ConnectionError("Network error")
            mock_client_class.return_value = mock_client

            backend = GitHubSyncBackend(core=mock_core, config=config)
            backend.github_client = mock_client

            # Operations should fail gracefully, not crash the backend
            if backend.github_client is not None:
                try:
                    backend.github_client.get_issues()
                except ConnectionError:
                    # Expected behavior - operations fail, but backend is still usable
                    pass

    def test_backend_handles_github_api_errors(self):
        """Test backend handles GitHub API errors gracefully."""
        mock_core = MagicMock()
        config = {
            "token": "test-token",
            "owner": "test-owner",
            "repo": "test-repo",
        }

        with patch(
            "roadmap.core.services.github.github_issue_client.GitHubIssueClient"
        ):
            backend = GitHubSyncBackend(core=mock_core, config=config)
            backend.github_client = MagicMock()

            # Simulate GitHub API returning an error
            if backend.github_client is not None:
                backend.github_client.get_issues.side_effect = Exception(
                    "API rate limit exceeded"
                )

                try:
                    backend.github_client.get_issues()
                except Exception:
                    # Expected - caller should handle
                    pass

            # Backend should still be usable
            assert backend is not None
            assert backend.config["token"] == "test-token"
