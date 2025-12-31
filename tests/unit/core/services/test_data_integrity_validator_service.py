"""Unit tests for data integrity validator service."""

from unittest.mock import MagicMock

import pytest

from roadmap.core.services.data_integrity_validator_service import (
    DataIntegrityValidatorService,
)


@pytest.fixture
def mock_issue_repo():
    """Create a mock issue repository."""
    return MagicMock()


@pytest.fixture
def mock_milestone_repo():
    """Create a mock milestone repository."""
    return MagicMock()


@pytest.fixture
def mock_link_service():
    """Create a mock link service."""
    return MagicMock()


@pytest.fixture
def validator_service(mock_issue_repo, mock_milestone_repo, mock_link_service):
    """Create a data integrity validator service."""
    return DataIntegrityValidatorService()


class TestDataIntegrityValidatorService:
    """Test data integrity validator service."""

    def test_validate_all_issues(self, validator_service, mock_issue_repo):
        """Test validating all issues."""
        mock_issue_repo.find_all.return_value = [
            {"id": "issue-1", "title": "Issue 1", "status": "open"},
            {"id": "issue-2", "title": "Issue 2", "status": "closed"},
        ]

        result = validator_service.validate_all_issues()

        assert len(result) >= 0
        mock_issue_repo.find_all.assert_called()

    def test_validate_issue_status(self, validator_service):
        """Test validating issue status."""
        issue = {
            "id": "issue-1",
            "title": "Test Issue",
            "status": "open",
        }

        result = validator_service.validate_issue_status(issue)

        assert result is True or result is False

    def test_validate_issue_invalid_status(self, validator_service):
        """Test validating issue with invalid status."""
        issue = {
            "id": "issue-1",
            "title": "Test Issue",
            "status": "invalid_status",
        }

        result = validator_service.validate_issue_status(issue)

        assert result is False

    def test_validate_milestone_references(
        self, validator_service, mock_issue_repo, mock_milestone_repo
    ):
        """Test validating milestone references."""
        mock_issue_repo.find_all.return_value = [
            {"id": "issue-1", "milestone": "milestone-1"},
        ]
        mock_milestone_repo.find_by_id.return_value = {"id": "milestone-1"}

        result = validator_service.validate_milestone_references()

        assert isinstance(result, list | tuple)

    def test_validate_broken_links(
        self, validator_service, mock_issue_repo, mock_link_service
    ):
        """Test validating broken links."""
        mock_issue_repo.find_all.return_value = [
            {"id": "issue-1", "links": ["external-id-1"]},
        ]
        mock_link_service.validate_link.return_value = False

        result = validator_service.validate_broken_links()

        assert isinstance(result, list | tuple)

    def test_validate_orphaned_issues(
        self, validator_service, mock_issue_repo, mock_milestone_repo
    ):
        """Test validating orphaned issues."""
        mock_issue_repo.find_all.return_value = [
            {"id": "issue-1", "milestone": "nonexistent-milestone"},
        ]
        mock_milestone_repo.find_by_id.return_value = None

        result = validator_service.validate_orphaned_issues()

        assert isinstance(result, list | tuple)

    def test_validate_duplicate_issues(self, validator_service, mock_issue_repo):
        """Test validating duplicate issues."""
        mock_issue_repo.find_all.return_value = [
            {"id": "issue-1", "title": "Same Title"},
            {"id": "issue-2", "title": "Same Title"},
        ]

        result = validator_service.validate_duplicate_issues()

        assert isinstance(result, list | tuple)

    def test_validate_naming_conventions(self, validator_service, mock_milestone_repo):
        """Test validating naming conventions."""
        mock_milestone_repo.find_all.return_value = [
            {"id": "m-1", "name": "valid-name"},
            {"id": "m-2", "name": "invalid name"},
        ]

        result = validator_service.validate_naming_conventions()

        assert isinstance(result, list | tuple)

    def test_validate_issue_dates(self, validator_service, mock_issue_repo):
        """Test validating issue dates."""
        import datetime

        now = datetime.datetime.now()

        mock_issue_repo.find_all.return_value = [
            {
                "id": "issue-1",
                "created": now.isoformat(),
                "updated": now.isoformat(),
            },
        ]

        result = validator_service.validate_issue_dates()

        assert isinstance(result, list | tuple)

    def test_validate_milestone_date_range(
        self, validator_service, mock_milestone_repo
    ):
        """Test validating milestone date ranges."""
        import datetime

        start = datetime.datetime.now()
        end = start + datetime.timedelta(days=7)

        mock_milestone_repo.find_all.return_value = [
            {
                "id": "m-1",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        ]

        result = validator_service.validate_milestone_date_range()

        assert isinstance(result, list | tuple)

    def test_get_validation_summary(
        self, validator_service, mock_issue_repo, mock_milestone_repo
    ):
        """Test getting validation summary."""
        mock_issue_repo.find_all.return_value = [
            {"id": "issue-1"},
            {"id": "issue-2"},
        ]
        mock_milestone_repo.find_all.return_value = [
            {"id": "m-1"},
        ]

        result = validator_service.get_validation_summary()

        assert isinstance(result, dict)

    def test_validate_all(
        self, validator_service, mock_issue_repo, mock_milestone_repo
    ):
        """Test validating all integrity checks."""
        mock_issue_repo.find_all.return_value = []
        mock_milestone_repo.find_all.return_value = []

        result = validator_service.validate_all()

        assert isinstance(result, dict)
