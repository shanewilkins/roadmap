"""Domain layer test fixtures and configuration.

Provides fixtures specific to domain/business logic testing,
including mock services, domain objects, and assertion helpers.
"""

from unittest.mock import Mock

import pytest

from tests.unit.domain.test_data_factory_generation import TestDataFactory


@pytest.fixture
def mock_issue_service():
    """Create a mock issue service for domain testing.

    Returns:
        Mock IssueService instance
    """
    service = Mock()
    service.create_issue.return_value = TestDataFactory.create_mock_issue()
    service.get_issue.return_value = TestDataFactory.create_mock_issue()
    service.update_issue.return_value = TestDataFactory.create_mock_issue()
    service.delete_issue.return_value = None
    service.list_issues.return_value = [TestDataFactory.create_mock_issue()]
    return service


@pytest.fixture
def mock_milestone_service():
    """Create a mock milestone service for domain testing.

    Returns:
        Mock MilestoneService instance
    """
    service = Mock()
    service.create_milestone.return_value = TestDataFactory.create_mock_milestone()
    service.get_milestone.return_value = TestDataFactory.create_mock_milestone()
    service.update_milestone.return_value = TestDataFactory.create_mock_milestone()
    service.delete_milestone.return_value = None
    service.list_milestones.return_value = [TestDataFactory.create_mock_milestone()]
    return service


@pytest.fixture
def mock_team_service():
    """Create a mock team service for domain testing.

    Returns:
        Mock TeamService instance
    """
    service = Mock()
    service.validate_assignee.return_value = (True, "user")
    service.get_canonical_assignee.return_value = "user"
    service.get_current_user.return_value = "test_user"
    service.list_team_members.return_value = ["user1", "user2", "user3"]
    return service


@pytest.fixture
def mock_storage():
    """Create a mock storage service for domain testing.

    Returns:
        Mock Storage instance
    """
    storage = Mock()
    storage.save.return_value = None
    storage.load.return_value = {}
    storage.delete.return_value = None
    storage.exists.return_value = True
    return storage


@pytest.fixture
def domain_test_data():
    """Provide access to TestDataFactory for domain tests.

    Returns:
        TestDataFactory class
    """
    return TestDataFactory
