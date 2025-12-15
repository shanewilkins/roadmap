"""GitHub integration fixtures.

Provides fixtures for GitHub webhook testing, API responses,
and GitHub client mocking.
"""

from unittest.mock import Mock, patch

import pytest

from tests.unit.domain.test_data_factory import TestDataFactory


@pytest.fixture
def github_webhook_payload():
    """Create GitHub webhook payload factory function.

    Returns a factory that creates realistic GitHub webhook payloads
    for testing webhook handlers.

    Returns:
        Factory function for creating GitHub webhook payloads
    """
    return TestDataFactory.create_github_webhook_payload


@pytest.fixture
def webhook_signature_creator():
    """Create webhook signature factory function.

    Returns a factory that creates valid webhook signatures
    for authenticating webhook requests.

    Returns:
        Factory function for creating webhook signatures
    """
    return TestDataFactory.create_webhook_signature


@pytest.fixture
def github_api_response():
    """Create GitHub API response factory function.

    Returns a factory that creates realistic GitHub API responses
    for testing API integrations.

    Returns:
        Factory function for creating GitHub API responses
    """
    return TestDataFactory.create_github_api_response


@pytest.fixture
def mock_github_client():
    """Mock GitHubClient for testing.

    Provides a mock GitHub client that simulates the behavior
    of the real GitHubClient without making actual API calls.

    Returns:
        Mock GitHub client instance
    """
    with patch("roadmap.sync.GitHubClient") as mock_client_class:
        mock_client = Mock()
        # Set up common methods and properties
        mock_client.is_authenticated = True
        mock_client.owner = "test-owner"
        mock_client.repo = "test-repo"
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def patch_github_integration():
    """Lightweight patch for GitHub integration to avoid heavy mocking.

    Provides a simple mock for GitHub integration testing.
    Note: enhanced_github_integration has been moved to future/ (post-1.0 feature).

    Returns:
        Mock GitHub integration instance
    """
    mock = Mock()
    mock.is_github_enabled.return_value = True
    mock.handle_push_event.return_value = []
    mock.handle_pull_request_event.return_value = []
    yield mock
