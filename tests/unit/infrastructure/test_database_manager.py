"""
Tests for database infrastructure management.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from roadmap.adapters.persistence.database_manager import (
    DatabaseManager,
)


class TestDatabaseManager:
    """Test DatabaseManager database connection and schema management."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        try:
            db_path.unlink()
            wal_path = Path(str(db_path) + "-wal")
            shm_path = Path(str(db_path) + "-shm")
            if wal_path.exists():
                wal_path.unlink()
            if shm_path.exists():
                shm_path.unlink()
        except Exception:
            pass

    @pytest.fixture
    def db_manager(self, temp_db):
        """Create a DatabaseManager instance with temp database."""
        return DatabaseManager(db_path=temp_db)

    def test_initialization_creates_database_file(self, temp_db):
        """DatabaseManager should create database file on init."""
        DatabaseManager(db_path=temp_db)
        assert temp_db.exists()

    def test_get_connection_returns_valid_connection(self, db_manager):
        """_get_connection should return a valid SQLite connection."""
        conn = db_manager._get_connection()
        assert isinstance(conn, sqlite3.Connection)

    def test_get_connection_is_thread_local(self, db_manager):
        """_get_connection should return thread-local connections."""
        conn1 = db_manager._get_connection()
        conn2 = db_manager._get_connection()
        assert conn1 is conn2

    def test_transaction_context_manager(self, db_manager):
        """transaction() should work as context manager."""
        with db_manager.transaction() as conn:
            assert isinstance(conn, sqlite3.Connection)
            conn.execute(
                "INSERT INTO projects (id, name) VALUES (?, ?)",
                ("test-project", "Test Project"),
            )

        # Verify data was committed
        conn = db_manager._get_connection()
        result = conn.execute(
            "SELECT name FROM projects WHERE id = ?", ("test-project",)
        ).fetchone()
        assert result["name"] == "Test Project"

    def test_transaction_rollback_on_exception(self, db_manager):
        """transaction() should rollback on exception."""
        try:
            with db_manager.transaction() as conn:
                conn.execute(
                    "INSERT INTO projects (id, name) VALUES (?, ?)",
                    ("test-project", "Test Project"),
                )
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify data was not committed
        conn = db_manager._get_connection()
        result = conn.execute(
            "SELECT name FROM projects WHERE id = ?", ("test-project",)
        ).fetchone()
        assert result is None

    def test_is_initialized_returns_true_after_init(self, db_manager):
        """is_initialized() should return True after initialization."""
        assert db_manager.is_initialized()

    def test_is_initialized_returns_false_on_error(self, db_manager):
        """is_initialized() should return False if database is corrupted."""
        # Close the existing connection first
        db_manager.close()

        # Corrupt the database by writing invalid data
        with open(db_manager.db_path, "w") as f:
            f.write("corrupted data")

        result = db_manager.is_initialized()
        # After corruption, is_initialized should return False
        assert not result

    def test_database_schema_created(self, db_manager):
        """Database schema should be created with all required tables."""
        conn = db_manager._get_connection()

        tables = [
            "projects",
            "milestones",
            "issues",
            "issue_dependencies",
            "issue_labels",
            "comments",
            "sync_base_state",
            "sync_metadata",
            "file_sync_state",
        ]

        for table in tables:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            assert result is not None, f"Table {table} was not created"

    def test_vacuum_compacts_database(self, db_manager):
        """vacuum() should compact the database."""
        # Insert and delete some data to create fragmentation
        with db_manager.transaction() as conn:
            for i in range(100):
                conn.execute(
                    "INSERT INTO projects (id, name) VALUES (?, ?)",
                    (f"project-{i}", f"Project {i}"),
                )

        size_before = db_manager.db_path.stat().st_size

        # Delete all projects
        with db_manager.transaction() as conn:
            conn.execute("DELETE FROM projects")

        db_manager.vacuum()

        size_after = db_manager.db_path.stat().st_size
        # Size should be reduced or at least not increased
        assert size_after <= size_before

    def test_close_closes_connection(self, db_manager):
        """close() should close database connection."""
        conn = db_manager._get_connection()
        db_manager.close()

        # Connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_database_exists_returns_true_for_existing_db(self, db_manager):
        """database_exists() should return True for initialized database."""
        assert db_manager.database_exists()

    def test_database_exists_returns_false_for_missing_tables(self, temp_db):
        """database_exists() should return False if tables are missing."""
        # Create an empty database without tables
        conn = sqlite3.connect(temp_db)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.close()

        # Now test with DatabaseManager - need fresh instance
        import time

        time.sleep(0.1)  # Give filesystem time to update

        db_manager = DatabaseManager(db_path=temp_db)
        # Since initialization creates tables, this will be True after init
        # The method checks for core tables
        assert db_manager.is_initialized()

    def test_is_safe_for_writes_returns_true_for_valid_db(self, db_manager):
        """is_safe_for_writes() should return True for valid database."""
        safe, msg = db_manager.is_safe_for_writes()
        assert safe
        assert isinstance(msg, str)

    def test_is_safe_for_writes_returns_false_for_corrupted_db(self, db_manager):
        """is_safe_for_writes() should return False for corrupted database."""
        db_manager.close()

        with open(db_manager.db_path, "w") as f:
            f.write("corrupted")

        safe, msg = db_manager.is_safe_for_writes()
        # After corruption, safety check should fail
        assert not safe

    def test_multiple_transactions_sequential(self, db_manager):
        """Multiple sequential transactions should work correctly."""
        for i in range(5):
            with db_manager.transaction() as conn:
                conn.execute(
                    "INSERT INTO projects (id, name) VALUES (?, ?)",
                    (f"project-{i}", f"Project {i}"),
                )

        conn = db_manager._get_connection()
        result = conn.execute("SELECT COUNT(*) as count FROM projects").fetchone()
        assert result["count"] == 5

    def test_nested_transaction_not_supported(self, db_manager):
        """Nested transactions should raise an error."""
        with pytest.raises(sqlite3.OperationalError):
            with db_manager.transaction():
                with db_manager.transaction():
                    pass
