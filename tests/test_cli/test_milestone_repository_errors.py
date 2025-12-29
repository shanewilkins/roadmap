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
from roadmap.common.errors.exceptions import CreateError, UpdateError


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


class TestMilestoneRepositoryGet:
    """Test milestone retrieval with various error scenarios."""

    def test_get_existing_milestone(self):
        """Test successful retrieval of existing milestone."""
        mock_get_connection = Mock()
        mock_row = {"id": "m1", "title": "v1.0", "status": "open"}
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        repo = MilestoneRepository(mock_get_connection, Mock())

        result = repo.get("m1")

        assert result == mock_row
        mock_conn.execute.assert_called_once()

    def test_get_nonexistent_milestone(self):
        """Test retrieval of non-existent milestone returns None."""
        mock_get_connection = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        repo = MilestoneRepository(mock_get_connection, Mock())

        result = repo.get("nonexistent")

        assert result is None

    def test_get_with_none_id(self):
        """Test get with None as milestone_id."""
        mock_get_connection = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

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
        mock_get_connection = Mock()
        mock_conn = Mock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("no such table")
        mock_get_connection.return_value = mock_conn

        repo = MilestoneRepository(mock_get_connection, Mock())

        with pytest.raises(sqlite3.OperationalError):
            repo.get("m1")

    def test_get_with_empty_string_id(self):
        """Test get with empty string as milestone_id."""
        mock_get_connection = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        repo = MilestoneRepository(mock_get_connection, Mock())

        result = repo.get("")

        assert result is None

    def test_get_with_very_long_id(self):
        """Test get with extremely long milestone_id."""
        mock_get_connection = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        repo = MilestoneRepository(mock_get_connection, Mock())

        long_id = "m" * 10000
        result = repo.get(long_id)

        assert result is None

    def test_get_row_conversion_error(self):
        """Test get when row dict conversion fails."""
        mock_get_connection = Mock()
        mock_conn = Mock()
        # Create a mock row that cannot be converted to dict
        mock_row = Mock(spec=[])  # Empty spec prevents attribute access
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        repo = MilestoneRepository(mock_get_connection, Mock())

        # Attempting to convert non-dict-like object raises TypeError
        with pytest.raises(TypeError):
            repo.get("m1")


class TestMilestoneRepositoryUpdate:
    """Test milestone update with various error scenarios."""

    def test_update_with_valid_updates(self):
        """Test successful update with valid fields."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.update("m1", {"title": "v2.0", "status": "closed"})

        assert result is True
        mock_conn.execute.assert_called_once()

    def test_update_with_no_changes(self):
        """Test update with empty updates dictionary."""
        mock_transaction = Mock()

        repo = MilestoneRepository(Mock(), mock_transaction)

        result = repo.update("m1", {})

        assert result is False
        mock_transaction.assert_not_called()

    def test_update_nonexistent_milestone(self):
        """Test update when milestone doesn't exist."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 0
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.update("nonexistent", {"title": "new title"})

        assert result is False

    def test_update_transaction_context_error(self):
        """Test update when transaction context manager fails."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_transaction.return_value.__enter__ = Mock(
            side_effect=sqlite3.Error("locked")
        )
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # safe_operation decorator wraps sqlite3.Error as UpdateError
        with pytest.raises(UpdateError):
            repo.update("m1", {"title": "new title"})

    def test_update_sql_execution_error(self):
        """Test update when SQL execution fails."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("syntax error")
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # safe_operation decorator wraps sqlite3.OperationalError as UpdateError
        with pytest.raises(UpdateError):
            repo.update("m1", {"title": "new title"})

    def test_update_with_single_field(self):
        """Test update with only one field."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.update("m1", {"title": "new title"})

        assert result is True

    def test_update_with_many_fields(self):
        """Test update with multiple fields."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        updates = {
            "title": "v2.0",
            "description": "New description",
            "status": "closed",
            "due_date": "2025-12-31",
            "metadata": '{"new": "metadata"}',
        }

        result = repo.update("m1", updates)

        assert result is True

    def test_update_with_none_values(self):
        """Test update with None values in updates."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.update("m1", {"title": None, "description": None})

        assert result is True

    def test_update_with_empty_string_values(self):
        """Test update with empty strings."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.update("m1", {"title": "", "description": ""})

        assert result is True

    def test_update_with_special_characters(self):
        """Test update with special characters."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        updates = {
            "title": "Title with 'quotes' and \"double quotes\"",
            "description": "Unicode: 🚀 ñ é ü",
        }

        result = repo.update("m1", updates)

        assert result is True


class TestMilestoneRepositoryMarkArchived:
    """Test milestone archive operations with error scenarios."""

    @pytest.mark.parametrize(
        "archived_flag,expected_sql_value,pass_flag",
        [
            (True, "archived = 1", True),
            (False, "archived = 0", False),
        ],
    )
    def test_mark_archived_variants(self, archived_flag, expected_sql_value, pass_flag):
        """Test marking milestone as archived/unarchived.

        Tests both archived=True and archived=False scenarios.
        """
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.mark_archived("m1", archived=archived_flag)

        assert result is True
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert expected_sql_value in call_args[0]

    def test_mark_archived_default_true(self):
        """Test mark_archived defaults to True when not specified."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.mark_archived("m1")

        assert result is True
        call_args = mock_conn.execute.call_args[0]
        assert "archived = 1" in call_args[0]

    def test_mark_archived_nonexistent_milestone(self):
        """Test mark_archived when milestone doesn't exist."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 0
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        result = repo.mark_archived("nonexistent")

        assert result is False

    def test_mark_archived_transaction_error(self):
        """Test mark_archived when transaction fails."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_transaction.return_value.__enter__ = Mock(
            side_effect=sqlite3.Error("locked")
        )
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # safe_operation decorator wraps sqlite3.Error as UpdateError
        with pytest.raises(UpdateError):
            repo.mark_archived("m1")

    def test_mark_archived_sql_error(self):
        """Test mark_archived when SQL execution fails."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("table locked")
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # safe_operation decorator wraps sqlite3.OperationalError as UpdateError
        with pytest.raises(UpdateError):
            repo.mark_archived("m1")

    def test_mark_archived_timestamp_handling(self):
        """Test mark_archived sets/clears timestamp correctly."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 1
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # Archive should set timestamp
        repo.mark_archived("m1", archived=True)
        call_args = mock_conn.execute.call_args[0]
        assert "CURRENT_TIMESTAMP" in call_args[0]

        # Unarchive should clear timestamp
        mock_conn.reset_mock()
        repo.mark_archived("m1", archived=False)
        call_args = mock_conn.execute.call_args[0]
        assert "archived_at = NULL" in call_args[0]


class TestMilestoneRepositoryConcurrency:
    """Test concurrent operation scenarios and race conditions."""

    def test_concurrent_create_same_id(self):
        """Test concurrent creation with same ID results in constraint error."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.IntegrityError(
            "UNIQUE constraint failed"
        )
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # safe_operation decorator wraps sqlite3.IntegrityError as CreateError
        with pytest.raises(CreateError):
            repo.create({"id": "m1", "title": "v1"})

    def test_concurrent_update_and_delete(self):
        """Test update after concurrent delete results in no rows updated."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.rowcount = 0
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_transaction.return_value.__exit__ = Mock(return_value=False)

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # Simulate update after delete
        result = repo.update("m1", {"title": "new"})

        assert result is False

    def test_transaction_rollback_on_error(self):
        """Test transaction rollback when error occurs."""
        mock_get_connection = Mock()
        mock_transaction = Mock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.IntegrityError("constraint failed")
        mock_transaction.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_exit = Mock(return_value=False)
        mock_transaction.return_value.__exit__ = mock_exit

        repo = MilestoneRepository(mock_get_connection, mock_transaction)

        # safe_operation decorator wraps sqlite3.IntegrityError as CreateError
        with pytest.raises(CreateError):
            repo.create({"id": "m1"})

        # Verify exit was called (allowing context manager cleanup)
        mock_exit.assert_called_once()


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
        mock_get_connection = Mock()
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.execute.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

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
