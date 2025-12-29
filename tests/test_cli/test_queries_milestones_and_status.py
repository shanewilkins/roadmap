"""Tests for QueryService read operations (queries.py module).

Tests for reading, querying, and filtering issues and milestones.
Covers list operations, filtering, and integration scenarios.
"""

import json
from unittest import mock

from roadmap.adapters.persistence.storage.queries import QueryService


class TestGetIssuesByStatus:
    """Test get_issues_by_status method for status distribution."""

    def test_get_issues_by_status_empty_database(self):
        """Test get_issues_by_status with no issues."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {}

    def test_get_issues_by_status_single_status(self):
        """Test get_issues_by_status with single status."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("open", 5)]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {"open": 5}

    def test_get_issues_by_status_multiple_statuses(self):
        """Test get_issues_by_status with multiple statuses."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        status_rows = [
            ("backlog", 12),
            ("closed", 45),
            ("in-progress", 8),
            ("open", 23),
        ]

        mock_conn.execute.return_value.fetchall.return_value = status_rows

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {
                "backlog": 12,
                "closed": 45,
                "in-progress": 8,
                "open": 23,
            }
            assert sum(result.values()) == 88

    def test_get_issues_by_status_database_error(self):
        """Test get_issues_by_status returns empty dict on error."""
        mock_state_manager = mock.MagicMock()

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.side_effect = Exception("Query failed")

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result == {}

    def test_get_issues_by_status_zero_counts(self):
        """Test get_issues_by_status includes statuses with zero issues."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        status_rows = [
            ("backlog", 0),
            ("closed", 10),
            ("in-progress", 0),
            ("open", 5),
        ]

        mock_conn.execute.return_value.fetchall.return_value = status_rows

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_issues_by_status()

            assert result["backlog"] == 0
            assert result["in-progress"] == 0


class TestQueryServiceIntegration:
    """Integration tests for QueryService operations."""

    def test_multiple_queries_same_transaction(self):
        """Test multiple query methods can share transaction context."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        # Setup different return values for different queries
        mock_conn.execute.return_value.fetchall.side_effect = [
            [],  # get_all_issues returns empty
            [],  # get_all_milestones returns empty
        ]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            issues = service.get_all_issues()
            milestones = service.get_all_milestones()

            assert issues == []
            assert milestones == []

    def test_query_service_with_metadata_consistency(self):
        """Test QueryService maintains consistency when parsing metadata."""
        mock_state_manager = mock.MagicMock()
        mock_conn = mock.MagicMock()

        # Create test data with metadata
        test_metadata = {"priority": "urgent", "custom": 123}
        metadata_json = json.dumps(test_metadata)

        issue_row = (
            "i-1",
            "Title",
            "open",
            "high",
            "bug",
            "user",
            5,
            "2024-12-01",
            "p1",
            "m1",
            metadata_json,
            "Milestone",
            "Project",
        )

        mock_conn.execute.return_value.fetchall.return_value = [issue_row]

        with mock.patch.object(mock_state_manager, "transaction") as mock_tx:
            mock_tx.return_value.__enter__.return_value = mock_conn

            service = QueryService(mock_state_manager)
            result = service.get_all_issues()

            # Metadata should be merged into result
            assert result[0]["priority"] == "urgent"
            assert result[0]["custom"] == 123
