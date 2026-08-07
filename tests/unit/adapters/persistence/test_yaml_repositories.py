"""Tests for YAMLIssueRepository (Phase 7 coverage)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.persistence.yaml_repositories import YAMLIssueRepository
from roadmap.core.domain.issue import Issue


class TestYAMLIssueRepository:
    """Test suite for YAMLIssueRepository."""

    @pytest.fixture
    def mock_db(self):
        """Create mock StateManager."""
        return MagicMock()

    @pytest.fixture
    def issues_dir(self, tmp_path):
        """Create temporary issues directory."""
        return tmp_path / "issues"

    @pytest.fixture
    def repository(self, mock_db, issues_dir):
        """Create YAMLIssueRepository instance."""
        issues_dir.mkdir(parents=True, exist_ok=True)
        return YAMLIssueRepository(mock_db, issues_dir)

    def test_init_stores_references(self, mock_db, issues_dir):
        """Test initialization stores db and issues_dir."""
        repo = YAMLIssueRepository(mock_db, issues_dir)

        assert repo.db is mock_db
        assert repo.issues_dir == issues_dir

    def test_get_returns_none_when_not_found(self, repository):
        """Test get returns None when issue not found."""
        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_with_filter.return_value = []

            result = repository.get("nonexistent")

        assert result is None

    def test_get_returns_issue_when_found(self, repository):
        """Test get returns issue when found."""
        mock_issue = MagicMock(spec=Issue)
        mock_issue.id = "issue-1"

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_with_filter.return_value = [mock_issue]

            result = repository.get("issue-1")

        assert result is mock_issue

    def test_list_returns_active_issues(self, repository):
        """Test list returns active issues only."""
        mock_issues = [
            MagicMock(
                spec=Issue, id="1", milestone=None, status=MagicMock(value="todo")
            ),
            MagicMock(
                spec=Issue, id="2", milestone="v1-0", status=MagicMock(value="todo")
            ),
        ]

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_and_parse.return_value = mock_issues

            result = repository.list()

        assert len(result) == 2
        assert result == mock_issues

    def test_list_filters_by_milestone(self, repository):
        """Test list filters by milestone."""
        mock_issue1 = MagicMock(
            spec=Issue, milestone="v1-0", status=MagicMock(value="todo")
        )
        mock_issue2 = MagicMock(
            spec=Issue, milestone="v2-0", status=MagicMock(value="todo")
        )

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_and_parse.return_value = [mock_issue1, mock_issue2]

            result = repository.list(milestone="v1-0")

        assert len(result) == 1
        assert result[0] == mock_issue1

    def test_list_filters_by_status(self, repository):
        """Test list filters by status."""
        mock_issue1 = MagicMock(
            spec=Issue, milestone=None, status=MagicMock(value="todo")
        )
        mock_issue2 = MagicMock(
            spec=Issue, milestone=None, status=MagicMock(value="closed")
        )

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            # Return both issues, let filter handle it
            mock_enum.enumerate_and_parse.return_value = [mock_issue1, mock_issue2]

            result = repository.list(status="todo")

        # Should filter to just the first one
        assert len(result) == 1
        assert result[0] == mock_issue1

    def test_list_all_including_archived(self, repository):
        """Test list_all_including_archived includes both active and archived."""
        mock_active = MagicMock(spec=Issue, id="1", milestone=None)
        mock_archived = MagicMock(spec=Issue, id="2", milestone=None)

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            # First call for active, second for archived
            mock_enum.enumerate_and_parse.side_effect = [[mock_active], [mock_archived]]

            with patch.object(Path, "exists", return_value=True):
                result = repository.list_all_including_archived()

        assert len(result) == 2
        assert mock_active in result
        assert mock_archived in result

    def test_list_all_handles_missing_archive(self, repository):
        """Test list_all_including_archived when archive directory doesn't exist."""
        mock_active = MagicMock(spec=Issue, id="1", milestone=None)

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_and_parse.return_value = [mock_active]

            with patch.object(Path, "exists", return_value=False):
                result = repository.list_all_including_archived()

        assert len(result) == 1
        assert result[0] == mock_active

    def test_list_all_filters_by_milestone(self, repository):
        """Test list_all_including_archived filters by milestone."""
        mock_active = MagicMock(
            spec=Issue, milestone="v1-0", status=MagicMock(value="todo")
        )
        mock_archived = MagicMock(
            spec=Issue, milestone="v2-0", status=MagicMock(value="closed")
        )

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_and_parse.side_effect = [[mock_active], [mock_archived]]

            with patch.object(Path, "exists", return_value=True):
                result = repository.list_all_including_archived(milestone="v1-0")

        assert len(result) == 1
        assert result[0] == mock_active

    def test_list_all_filters_by_status(self, repository):
        """Test list_all_including_archived filters by status."""
        mock_active = MagicMock(
            spec=Issue, milestone=None, status=MagicMock(value="todo")
        )
        mock_archived = MagicMock(
            spec=Issue, milestone=None, status=MagicMock(value="closed")
        )

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            # Return both, let filter handle it
            mock_enum.enumerate_and_parse.side_effect = [[mock_active], [mock_archived]]

            with patch.object(Path, "exists", return_value=True):
                result = repository.list_all_including_archived(status="todo")

        # Should filter to just active
        assert len(result) == 1
        assert result[0] == mock_active

    def test_list_returns_empty_when_no_issues(self, repository):
        """Test list returns empty list when no issues found."""
        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_and_parse.return_value = []

            result = repository.list()

        assert result == []

    def test_list_all_returns_empty_when_no_issues(self, repository):
        """Test list_all_including_archived returns empty when no issues."""
        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_and_parse.return_value = []

            with patch.object(Path, "exists", return_value=False):
                result = repository.list_all_including_archived()

        assert result == []


class TestYAMLIssueRepositoryIntegration:
    """Integration tests for YAMLIssueRepository."""

    def test_get_with_partial_id_match(self):
        """Test get matches partial issue ID."""
        mock_db = MagicMock()
        issues_dir = Path("/tmp/issues")

        repo = YAMLIssueRepository(mock_db, issues_dir)
        mock_issue = MagicMock(spec=Issue)
        mock_issue.id = "issue-12345"

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_with_filter.return_value = [mock_issue]

            result = repo.get("issue-123")

        assert result is mock_issue

    def test_list_with_multiple_filters(self):
        """Test list applies multiple filters correctly."""
        mock_db = MagicMock()
        issues_dir = Path("/tmp/issues")
        repo = YAMLIssueRepository(mock_db, issues_dir)

        mock_issue = MagicMock(
            spec=Issue, milestone="v1-0", status=MagicMock(value="todo")
        )
        mock_other = MagicMock(
            spec=Issue, milestone="v2-0", status=MagicMock(value="closed")
        )

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            # Return both, let filter handle filtering
            mock_enum.enumerate_and_parse.return_value = [mock_issue, mock_other]

            result = repo.list(milestone="v1-0", status="todo")

        # Should filter to match both criteria
        assert len(result) == 1
        assert result[0] == mock_issue

    def test_list_all_with_mixed_archives(self):
        """Test list_all_including_archived properly combines active and archived."""
        mock_db = MagicMock()
        issues_dir = Path("/tmp/issues")
        repo = YAMLIssueRepository(mock_db, issues_dir)

        mock_active_issues = [MagicMock(spec=Issue, id=f"active-{i}") for i in range(3)]
        mock_archived_issues = [
            MagicMock(spec=Issue, id=f"archived-{i}") for i in range(2)
        ]

        with patch(
            "roadmap.adapters.persistence.yaml_repositories.FileEnumerationService"
        ) as mock_enum:
            mock_enum.enumerate_and_parse.side_effect = [
                mock_active_issues,
                mock_archived_issues,
            ]

            with patch.object(Path, "exists", return_value=True):
                result = repo.list_all_including_archived()

        assert len(result) == 5
        assert all(issue in result for issue in mock_active_issues)
        assert all(issue in result for issue in mock_archived_issues)
