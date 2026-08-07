"""Comprehensive tests for DatabaseManager covering uncovered error paths.

Tests for transaction context manager, initialization errors,
and safety check error handling.
"""

import sqlite3
from unittest.mock import MagicMock

import pytest

from roadmap.adapters.persistence.database_manager import (
    DatabaseManager,
)


class TestDatabaseManagerTransaction:
    """Tests for transaction context manager error paths."""

    def test_transaction_rollback_on_operational_error(self, tmp_path):
        """Transaction handles OperationalError during rollback."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Mock the connection to simulate rollback failure
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = [
            None,  # BEGIN IMMEDIATE succeeds
            Exception("Simulated error in yield block"),  # Error during transaction
            sqlite3.OperationalError("Transaction not active"),  # ROLLBACK fails
        ]

        manager._local.connection = mock_conn

        with pytest.raises(Exception) as exc_info:
            with manager.transaction():
                raise Exception("Simulated error in yield block")

        assert "Simulated error in yield block" in str(exc_info.value)
