"""Conftest for sync adapter tests - patches remote API clients."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_github_issue_client(monkeypatch):
    """Auto-mock GitHubIssueClient to prevent API calls in all sync tests."""
    mock_class = MagicMock()
    mock_instance = MagicMock()
    mock_instance.fetch_issue = MagicMock(return_value={})
    mock_instance.fetch_issues = MagicMock(return_value={})
    mock_class.return_value = mock_instance

    # Patch at the source
    monkeypatch.setattr(
        "roadmap.core.services.github.github_issue_client.GitHubIssueClient",
        mock_class,
    )
    yield mock_class
