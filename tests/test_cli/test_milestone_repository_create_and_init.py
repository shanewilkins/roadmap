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
from roadmap.common.errors.exceptions import CreateError


class TestMilestoneRepositoryInitialization:
    """Test repository initialization and dependency injection."""

    @pytest.mark.parametrize(
        "get_conn,trans,expected_conn,expected_trans",
        [
            (Mock(), Mock(), True, True),
            (None, Mock(), False, True),
            (Mock(), None, True, False),
        ],
    )
    def test_init_various(self, get_conn, trans, expected_conn, expected_trans):
        repo = MilestoneRepository(get_conn, trans)
        assert (repo._get_connection is not None) == expected_conn
        assert (repo._transaction is not None) == expected_trans

    def test_init_preserves_callable_references(self):
        mock_get_connection = Mock(return_value="connection")
        mock_transaction = Mock()
        repo = MilestoneRepository(mock_get_connection, mock_transaction)
        assert repo._get_connection is mock_get_connection
        assert repo._transaction is mock_transaction


class TestMilestoneRepositoryCreate:
    """Test milestone creation with various error scenarios."""

    def test_create_with_valid_data(self):
        """Test successful creation of milestone with all fields."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {
            "id": "m1",
            "project_id": "p1",
            "title": "v1.0",
            "description": "Version 1.0",
            "status": "open",
            "due_date": "2024-12-31",
            "metadata": '{"key": "value"}',
        }

        result = repo.create(milestone_data)

        assert result == "m1"
        mock_transaction.assert_called_once()
        mock_conn.execute.assert_called_once()

    def test_create_with_minimal_data(self):
        """Test creation with only required fields."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {"id": "m1"}

        result = repo.create(milestone_data)

        assert result == "m1"
        # Verify execute was called with proper substitution
        call_args = mock_conn.execute.call_args[0]
        assert "INSERT INTO milestones" in call_args[0]

    def test_create_with_missing_id(self):
        """Test creation raises error when id is missing."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {
            "project_id": "p1",
            "title": "v1.0",
        }

        # safe_operation decorator wraps KeyError as CreateError
        with pytest.raises(CreateError):
            repo.create(milestone_data)

    def test_create_transaction_context_manager_error(self):
        """Test creation handles transaction context manager failures."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_transaction.return_value.__enter__ = Mock(
            side_effect=sqlite3.Error("DB locked")
        )
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {"id": "m1", "title": "v1.0"}

        # safe_operation decorator wraps sqlite3.Error as CreateError
        with pytest.raises(CreateError):
            repo.create(milestone_data)

    def test_create_sql_execute_error(self):
        """Test creation when SQL execution fails."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.IntegrityError(
            "UNIQUE constraint failed"
        )
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {"id": "m1", "title": "v1.0"}

        # safe_operation decorator wraps sqlite3.IntegrityError as CreateError
        with pytest.raises(CreateError):
            repo.create(milestone_data)

    def test_create_with_none_values_in_optional_fields(self):
        """Test creation with explicit None values in optional fields."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {
            "id": "m1",
            "project_id": None,
            "title": None,
            "description": None,
            "due_date": None,
            "metadata": None,
        }

        result = repo.create(milestone_data)

        assert result == "m1"
        # Verify None values are passed correctly
        call_args = mock_conn.execute.call_args
        assert call_args[0][1][1] is None  # project_id position

    def test_create_with_empty_string_fields(self):
        """Test creation with empty string values."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {
            "id": "m1",
            "project_id": "",
            "title": "",
            "description": "",
        }

        result = repo.create(milestone_data)

        assert result == "m1"

    def test_create_with_special_characters_in_data(self):
        """Test creation with special characters and SQL injection attempts."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        milestone_data = {
            "id": "m1'; DROP TABLE milestones; --",
            "title": "Title with 'quotes' and \"double quotes\"",
            "description": "Unicode: 🚀 ñ é ü",
        }

        result = repo.create(milestone_data)

        assert result == "m1'; DROP TABLE milestones; --"
        # Verify parameterized query usage (safe from SQL injection)
        call_args = mock_conn.execute.call_args
        assert len(call_args[0]) == 2  # Query and parameters

    def test_create_with_large_data(self):
        """Test creation with very large field values."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        large_description = "x" * 100000

        milestone_data = {
            "id": "m1",
            "title": "v1.0",
            "description": large_description,
        }

        result = repo.create(milestone_data)

        assert result == "m1"
