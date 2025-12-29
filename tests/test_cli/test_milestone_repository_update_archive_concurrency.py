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
