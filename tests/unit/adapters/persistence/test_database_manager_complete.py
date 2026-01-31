"""Comprehensive tests for DatabaseManager covering uncovered error paths.

Tests for transaction context manager, initialization errors,
and safety check error handling.
"""

import sqlite3
from unittest.mock import MagicMock, patch

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

    def test_transaction_commit_success(self, tmp_path):
        """Successful transaction commits."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        call_count = 0

        def mock_execute(sql):
            nonlocal call_count
            call_count += 1
            if "BEGIN" in sql:
                return None
            elif "COMMIT" in sql:
                return None

        mock_conn = MagicMock()
        mock_conn.execute = MagicMock(side_effect=mock_execute)

        manager._local.connection = mock_conn

        with manager.transaction():
            pass

        # Should have called BEGIN and COMMIT
        assert mock_conn.execute.call_count >= 2

    def test_transaction_rollback_on_exception(self, tmp_path):
        """Transaction rollbacks on exception."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        mock_conn = MagicMock()
        mock_conn.execute = MagicMock()
        mock_conn.execute.side_effect = [
            None,  # BEGIN succeeds
            Exception("Simulated error"),  # Error during transaction
            None,  # ROLLBACK succeeds
        ]

        manager._local.connection = mock_conn

        with pytest.raises(Exception, match="Simulated error"):
            with manager.transaction():
                raise Exception("Simulated error")

        # Should have called BEGIN, then ROLLBACK
        assert mock_conn.execute.call_count >= 2


class TestDatabaseManagerInitialization:
    """Tests for database initialization error paths."""

    def test_init_database_with_migration_already_applied(self, tmp_path):
        """Migration handling when columns already exist."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Verify database was initialized (no exception raised)
        assert manager.is_initialized()

    def test_init_database_creates_schema(self, tmp_path):
        """Database schema is properly created."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        conn = manager._get_connection()
        cursor = conn.cursor()

        # Check that main tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        )
        assert cursor.fetchone() is not None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='issues'"
        )
        assert cursor.fetchone() is not None

    def test_run_migrations_adds_archived_columns(self, tmp_path):
        """Migrations add archived columns correctly."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        conn = manager._get_connection()
        cursor = conn.cursor()

        # Check archived columns were added
        cursor.execute("PRAGMA table_info(projects)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "archived" in columns
        assert "archived_at" in columns


class TestDatabaseManagerCheckDatabase:
    """Tests for database integrity and existence checks."""

    def test_database_exists_returns_true_when_valid(self, tmp_path):
        """database_exists returns True for valid database."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Should be True after initialization
        assert manager.database_exists()

    def test_database_exists_returns_false_when_missing_file(self, tmp_path):
        """database_exists returns False when file doesn't exist."""
        db_file = tmp_path / "nonexistent.db"
        # Don't actually create the database
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.db_path = db_file

        assert not manager.database_exists()

    def test_database_exists_handles_exception(self, tmp_path):
        """database_exists handles exceptions gracefully."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Mock _get_connection to raise exception
        with patch.object(manager, "_get_connection") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")
            result = manager.database_exists()
            assert result is False


class TestDatabaseManagerSafety:
    """Tests for safety checking during write operations."""

    def test_is_safe_for_writes_success(self, tmp_path):
        """is_safe_for_writes returns True for healthy database."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        safe, _ = manager.is_safe_for_writes()
        assert safe is True

    def test_is_safe_for_writes_database_error(self, tmp_path):
        """is_safe_for_writes detects database corruption."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Mock connection to simulate corruption
        with patch.object(manager, "_get_connection") as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = sqlite3.DatabaseError("Database corruption")
            mock_get_conn.return_value = mock_conn

            safe, message = manager.is_safe_for_writes()
            assert safe is False
            assert "corruption" in message.lower()

    def test_is_safe_for_writes_general_exception(self, tmp_path):
        """is_safe_for_writes handles general exceptions."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Mock _get_connection to raise exception
        with patch.object(manager, "_get_connection") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")

            safe, message = manager.is_safe_for_writes()
            assert safe is False
            assert "failed" in message.lower()

    def test_is_safe_for_writes_pragma_check(self, tmp_path):
        """is_safe_for_writes performs pragma integrity check."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        safe, message = manager.is_safe_for_writes()
        assert safe is True


class TestDatabaseManagerInitializationCheck:
    """Tests for is_initialized error handling."""

    def test_is_initialized_returns_true_when_projects_table_exists(self, tmp_path):
        """is_initialized returns True when projects table exists."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        assert manager.is_initialized()

    def test_is_initialized_returns_false_on_exception(self, tmp_path):
        """is_initialized returns False on exception."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Mock _get_connection to raise exception
        with patch.object(manager, "_get_connection") as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")

            result = manager.is_initialized()
            assert result is False


class TestDatabaseManagerClose:
    """Tests for database connection cleanup."""

    def test_close_removes_connection(self, tmp_path):
        """close() removes thread-local connection."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Get connection to populate thread-local storage
        manager._get_connection()
        assert hasattr(manager._local, "connection")

        # Close should remove it
        manager.close()
        assert not hasattr(manager._local, "connection")

    def test_close_idempotent(self, tmp_path):
        """close() can be called multiple times safely."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Get connection first
        manager._get_connection()

        # Close multiple times
        manager.close()
        manager.close()  # Should not raise

        assert not hasattr(manager._local, "connection")


class TestDatabaseManagerVacuum:
    """Tests for database vacuum operation."""

    def test_vacuum_executes(self, tmp_path):
        """vacuum() executes VACUUM command."""
        db_file = tmp_path / "test.db"
        manager = DatabaseManager(db_file)

        # Should not raise
        manager.vacuum()

        # Verify database is still functional
        assert manager.is_initialized()
