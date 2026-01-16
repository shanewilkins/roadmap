"""Error path tests for milestone_repository module.

Tests focus on error handling, edge cases, and failure scenarios in the
MilestoneRepository class which handles all milestone-related database operations.

Tier 2 test coverage module addressing:
- Database connection failures
- Transaction error handling
- Invalid data validation
- Partial operation failures
- Concurrent modification scenarios
- Resource cleanup and rollback
"""

import sqlite3
from unittest.mock import MagicMock, Mock

import pytest

from roadmap.adapters.persistence.repositories.milestone_repository import (
    MilestoneRepository,
)
from roadmap.common.errors.exceptions import UpdateError
from tests.fixtures.mock_builders import build_mock_database_connection


class TestMilestoneRepositoryGet:
    """Test milestone retrieval with various error scenarios."""

    def test_get_existing_milestone(self):
        """Test successful retrieval of existing milestone."""
        mock_row = {"id": "m1", "title": "v1.0", "status": "open"}
        mock_get_connection, mock_conn = build_mock_database_connection(
            fetch_result=mock_row
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        result = repo.get("m1")

        assert result == mock_row
        mock_conn.execute.assert_called_once()

    def test_get_nonexistent_milestone(self):
        """Test retrieval of non-existent milestone returns None."""
        mock_get_connection, mock_conn = build_mock_database_connection(
            fetch_result=None
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        result = repo.get("nonexistent")

        assert result is None

    def test_get_with_none_id(self):
        """Test get with None as milestone_id."""
        mock_get_connection, mock_conn = build_mock_database_connection(
            fetch_result=None
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        result = repo.get(None)  # type: ignore

        assert result is None
        mock_conn.execute.assert_called_once()

    def test_get_database_connection_failure(self):
        """Test get when connection callable fails."""
        mock_get_connection = Mock(side_effect=sqlite3.Error("Connection failed"))

        repo = MilestoneRepository(mock_get_connection, Mock())

        with pytest.raises(sqlite3.Error):
            repo.get("m1")

    def test_get_sql_execution_error(self):
        """Test get when SQL execution fails."""
        mock_get_connection, mock_conn = build_mock_database_connection(
            execute_side_effect=sqlite3.OperationalError("no such table")
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        with pytest.raises(sqlite3.OperationalError):
            repo.get("m1")

    def test_get_with_empty_string_id(self):
        """Test get with empty string as milestone_id."""
        mock_get_connection, mock_conn = build_mock_database_connection(
            fetch_result=None
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        result = repo.get("")

        assert result is None

    def test_get_with_very_long_id(self):
        """Test get with extremely long milestone_id."""
        mock_get_connection, mock_conn = build_mock_database_connection(
            fetch_result=None
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        long_id = "m" * 10000
        result = repo.get(long_id)

        assert result is None

    def test_get_row_conversion_error(self):
        """Test get when row dict conversion fails."""
        # Create a mock row that cannot be converted to dict
        mock_row = Mock(spec=[])  # Empty spec prevents attribute access
        mock_get_connection, mock_conn = build_mock_database_connection(
            fetch_result=mock_row
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        # Attempting to convert non-dict-like object raises TypeError
        with pytest.raises(TypeError):
            repo.get("m1")


class TestMilestoneRepositoryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_create_with_dict_subclass(self):
        """Test creation with dict subclass instead of plain dict."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        class CustomDict(dict):
            pass

        milestone_data = CustomDict({"id": "m1", "title": "v1.0"})
        result = repo.create(milestone_data)

        assert result == "m1"

    def test_get_with_integer_id(self):
        """Test get with integer ID (type mismatch)."""
        mock_get_connection, mock_conn = build_mock_database_connection(
            fetch_result=None
        )

        repo = MilestoneRepository(mock_get_connection, Mock())

        # Should work as parameters are bound
        result = repo.get(123)  # type: ignore

        assert result is None
        mock_conn.execute.assert_called_once()

    def test_update_with_boolean_values(self):
        """Test update with boolean values."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.update("m1", {"archived": True})

        assert result is True

    def test_multiple_operations_sequence(self):
        """Test sequence of operations without isolation issues."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # Multiple creates
        repo.create({"id": "m1", "title": "v1"})
        repo.create({"id": "m2", "title": "v2"})

        # Multiple updates
        repo.update("m1", {"status": "closed"})
        repo.update("m2", {"status": "closed"})

        # Multiple archives
        repo.mark_archived("m1")
        repo.mark_archived("m2", archived=False)

        assert mock_conn.execute.call_count >= 6


class TestMilestoneRepositoryIntegration:
    """Test integration scenarios combining multiple operations."""

    def test_create_then_get(self):
        """Test create followed by get operation."""
        # Create operation
        mock_transaction = Mock()
        mock_conn_create = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn_create)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        # Get operation
        mock_get_connection = Mock()
        mock_conn_get = Mock()
        expected_row = {"id": "m1", "title": "v1", "status": "open"}
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = expected_row
        mock_conn_get.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn_get

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # Create
        created_id = repo.create({"id": "m1", "title": "v1"})
        assert created_id == "m1"

        # Get
        retrieved = repo.get("m1")
        assert retrieved == expected_row

    def test_create_update_archive_sequence(self):
        """Test full lifecycle: create, update, archive."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # Create
        created_id = repo.create({"id": "m1", "title": "v1"})
        assert created_id == "m1"

        # Update
        updated = repo.update("m1", {"status": "in_progress"})
        assert updated is True

        # Archive
        archived = repo.mark_archived("m1")
        assert archived is True

    def test_error_recovery_in_sequence(self):
        """Test error handling in operation sequence."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()

        # First create succeeds
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # Successful create
        created_id = repo.create({"id": "m1", "title": "v1"})
        assert created_id == "m1"

        # Simulate error in update - safe_operation wraps as UpdateError
        mock_conn.execute.side_effect = sqlite3.OperationalError("table locked")

        with pytest.raises(UpdateError):
            repo.update("m1", {"status": "closed"})

        # Verify repo still functional by resetting mock
        mock_conn.execute.side_effect = None
        mock_conn.execute.return_value.rowcount = 1

        # This should work again
        result = repo.mark_archived("m1")
        assert result is True
